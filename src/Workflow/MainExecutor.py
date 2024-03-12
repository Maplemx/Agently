import logging
import uuid
from .utils.exec_tree import create_empty_data_slot
from .utils.logger import get_default_logger
from .utils.find import find_by_attr
from .lib.BreakingHub import BreakingHub
from .lib.Store import Store

class MainExecutor:
    def __init__(self, workflow_id, settings={}):
        self.workflow_id = workflow_id
        self.is_running = True
        self.running_status = 'idle'
        self.settings = settings
        self.max_execution_limit = (settings or {}).get('max_execution_limit') or 10
        self.breaking_hub = BreakingHub(
            breaking_handler = self._handle_breaking,
            max_execution_limit=self.max_execution_limit
        )
        self.store = Store()
        if self.settings.get_trace_back("is_debug"):
            workflow_default_logger = get_default_logger(self.workflow_id, logging.INFO)
        else:
            workflow_default_logger = get_default_logger(self.workflow_id, logging.WARNING)
        self.logger = settings.get('logger', workflow_default_logger)
        # 已注册的执行器类型
        self.registed_executors = {}
        self.chunks_map = {}

    def start(self, runtime_data: dict):
        entries = runtime_data.get('entries') or []
        self.chunks_map = runtime_data.get('chunk_map') or {}
        self._reset_temp_status()
        self.running_status = 'start'

        self._execute_main(entries)
        self.running_status = 'end'

    def regist_executor(self, name: str, executor):
        """
        注册执行器，传入执行器的名称及executor
        """
        self.registed_executors[name] = executor

    def unregist_executor(self, name: str):
        """
        取消注册执行器，传入执行器的名称
        """
        if name in self.registed_executors:
            del self.registed_executors[name]

        return self

    def handle_command(self, data):
        """
        用于接收处理外部指令
        """
        if data is None or self.is_running == False or data["dataset"] is None:
            return

        command = data["dataset"]["command"]
        command_data = data["dataset"]["data"]
        if command == "input":
            if command_data and command_data["content"] and command_data['schema']:
                self.input(command_data["content"], command_data['schema'])
        elif command == "destroy":
            self.is_running = False
    
    def _execute_main(self, entries: list):
        """执行入口"""
        for entry_chunk in entries:
            slow_tasks = []
            self._execute_partial(
                entry_chunk,
                slow_tasks=slow_tasks,
                executing_ids=[],
                visited_record=[]
            )
            # 如果执行完成后，还有待执行任务，则需手动执行
            if len(slow_tasks) > 0:
                self._execute_slow_tasks(slow_tasks)
        

    def _execute_partial(
            self,
            chunk,
            slow_tasks = [], # 缓执行任务
            executing_ids = [], # 执行中的任务
            visited_record = [], # 已执行记录
        ):
        """执行某个分组，在单次分组里，不会存在循环节点，遇到循环节点，会另起一个分组执行"""

        # 针对循环，存入缓执行组中，延后执行
        if chunk['id'] in visited_record:
            if chunk.get('loop_entry') == True:
                slow_tasks.append(chunk)
            return

        # 1、校验上游依赖是否就绪
        if not self._check_dep_ready(chunk):
            self.logger.info(f"'{self._get_chunk_title(chunk)}' dependencies not ready.")
            return


        # 2、执行当前 chunk
        execute_id = uuid.uuid4()
        executing_ids.append(execute_id)
        self.logger.info(f"Execute '{self._get_chunk_title(chunk)}'")
        exec_value =  self._exec_chunk_core(chunk)
        self.breaking_hub.recoder(chunk)  # 更新中断器信息
        visited_record.append(chunk['id']) # 更新执行记录
        
        # 3、执行完成后，继续下游任务
        # 提取当前执行的结果，尝试将当前执行结果注入到下游的运行依赖插槽上 next_chunk['deps'][]['data_slot'] = 'xxx'
        for next_info in chunk['next_chunks']:
            next_chunk = self.chunks_map.get(next_info['id'])
            if not next_chunk:
                continue

            # 针对目标 chunk 的目标 handle 的插槽位，注入最新的值（注意如果是条件连接线，需要在条件满足时才更新）
            for next_rel_handle in next_info['handles']:
                source_handle = next_rel_handle['source_handle']
                target_handle = next_rel_handle['handle']
                source_value = exec_value.get(source_handle) if isinstance(exec_value, dict) else exec_value

                # 有条件的情况下，仅在条件满足时，才更新下游节点的数据
                condition_call = next_rel_handle.get('condition')
                if condition_call:
                    judge_res = condition_call(source_value)
                    if judge_res != True:
                        continue
                
                next_chunk_target_dep = find_by_attr(next_chunk['deps'], 'handle', target_handle)
                if next_chunk_target_dep:
                    next_chunk_target_dep['data_slot'] = {
                        'is_ready': True,
                        'updator': chunk['id'],
                        'value': source_value,
                    }

        # 依次尝试执行下游节点
        for next_info in chunk['next_chunks']:
            next_chunk = self.chunks_map.get(next_info['id'])
            if not next_chunk:
                continue

            self._execute_partial(next_chunk, slow_tasks, executing_ids, visited_record)
        
        # 任务执行完后，清理执行中的状态
        executing_ids.remove(execute_id)
        # 尝试执行缓执行任务
        if len(executing_ids) == 0:
            self._execute_slow_tasks(slow_tasks)
            slow_tasks.clear()

    def _execute_slow_tasks(self, slow_tasks):
        """尝试执行低优任务"""
        if len(slow_tasks) == 0:
            return

        for chunk in slow_tasks:
            # 先清空下游所有节点数据
            self._chunks_clean_walker(chunk)
            # 再启动执行
            self._execute_partial(
                chunk,
                slow_tasks=[],
                executing_ids=[],
                visited_record=[]
            )
            # if len(other_slow_tasks) > 0:
            #     self._execute_slow_tasks(other_slow_tasks)

    def _get_chunk_executor(self, name: str):
        """
        根据类型名称获取执行器
        """
        return self.registed_executors.get(name)

    def _reset_temp_status(self):
        """
        重置临时状态
        """
        self.running_status = 'idle'
        # 中断处理
        self.breaking_hub = BreakingHub(
            breaking_handler=self._handle_breaking,
            max_execution_limit=self.max_execution_limit
        )

    def _get_chunk_res_setter_key(self, chunk):
        """
        获取存储数据的 key（需要考虑循环调用的场景）
        """
        return f"{chunk['id']}_{self.breaking_hub.get_counts(chunk) + 1}"

    def _get_chunk_res_getter_key(self, chunk):
        """
        获取读取数据的 key（需要考虑循环调用的场景）
        """
        return f"{chunk['id']}_{self.breaking_hub.get_counts(chunk)}"

    def _exec_chunk_core(self, chunk):
        """
        执行任务（执行到此处的都是上游数据已就绪了的）
        """
        # 简化参数
        deps_dict = {}
        for dep in chunk['deps']:
            deps_dict[dep['handle']] = dep['data_slot']['value']

        # 交给执行器执行
        executor_type = chunk['data']['type']
        chunk_executor = self._get_chunk_executor(executor_type) or chunk.get('executor')
        exec_res = None
        try:
            exec_res = chunk_executor(deps_dict, self.store)
        except Exception as e:
            self.logger.error(f"Node Execution Exception: '{self._get_chunk_title(chunk)}'({chunk['id']}) {e}")
            # 主动中断执行
            raise Exception(e)

        return exec_res

    def _check_dep_ready(self, chunk):
        """监测依赖是否就绪"""
        deps = chunk.get('deps', [])
        if len(deps) == 0:
            return True

        for dep in deps:
            if dep['data_slot']['is_ready'] == False:
                return False
        return True

    def _chunks_clean_walker(self, root_chunk):
        """尝试对某个节点以下的分支做一轮清理工作"""

        visited_record = []
        def clean_core(chunk):
            for next_info in chunk['next_chunks']:
                next_chunk = self.chunks_map.get(next_info['id'])
                if not next_chunk:
                    continue

                if (next_chunk['id'] in visited_record) or (next_chunk['id'] == root_chunk['id']):
                    continue

                visited_record.append(next_chunk['id'])
                effect_handles = [handle_desc['handle'] for handle_desc in next_info['handles']]
                for dep in next_chunk['deps']:
                    data_slot = dep['data_slot']
                    # 如果当前的输入句柄受上游影响了，则重置
                    if (dep['handle'] in effect_handles) and (data_slot['updator'] == '' or data_slot['updator'] == chunk['id']):
                        dep['data_slot'] = create_empty_data_slot(next_chunk)

                clean_core(next_chunk)

        clean_core(root_chunk)
        
    
    def _get_chunk_title(self, chunk):
        return chunk["data"]["title"] or f'chunk-{chunk["data"]["id"]}' or 'Unknow chunk'

    def _handle_breaking(self, chunk, type):
        """处理中断"""
        self.logger.error(
            f"Exceeded maximum execution limit: {self._get_chunk_title(chunk)}")
        # 中断之前处理相关逻辑
        # 主动中断执行
        raise Exception(
            f"Exceeded maximum execution limit: {self._get_chunk_title(chunk)}")
