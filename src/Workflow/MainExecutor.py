import logging
import uuid
from .utils.exec_tree import disable_chunk_dep_ticket, create_new_chunk_slot_with_val
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
        workflow_default_logger = get_default_logger(self.workflow_id, level=logging.DEBUG if self.settings.get_trace_back("is_debug") else logging.WARN)
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
            slow_tasks: list, # 缓执行任务
            executing_ids: list, # 执行中的任务
            visited_record: list # 已执行记录
        ):
        """一组分组执行的核心方法"""

        # 1、执行当前 chunk
        has_been_executed = self._execute_single_chunk(
            chunk=chunk,
            slow_tasks=slow_tasks,
            executing_ids=executing_ids,
            visited_record=visited_record
        )
        # 如果根本未执行过（如无执行票据），直接返回
        if not has_been_executed:
            return

        # 2、依次先单独执行下游直接子 chunk 自身
        executed_child_chunks = []
        for next_info in chunk['next_chunks']:
            next_chunk = self.chunks_map.get(next_info['id'])
            if not next_chunk:
                continue

            self.logger.debug(f"From chunk '{self._get_chunk_title(chunk)}' call next chunk '{self._get_chunk_title(next_chunk)}'")
            child_executed = self._execute_single_chunk(
                chunk=next_chunk,
                slow_tasks=slow_tasks,
                executing_ids=executing_ids,
                visited_record=visited_record
            )
            # 成功执行的塞入记录中（用于稍后处理其后续的chunk）
            if child_executed:
                executed_child_chunks.append(next_chunk['id'])

        # 3、然后再依次递归处理已执行了的下游直接子节点的下级节点
        for next_child_id in executed_child_chunks:
            next_chunk = self.chunks_map.get(next_child_id)
            # 找不到定义，或者压根之前未成功执行时，则直接
            if not next_chunk:
                continue

            grandchild_chunks = next_chunk.get('next_chunks') or []
            for grandchild_chunk_info in grandchild_chunks:
                grandchild_chunk = self.chunks_map.get(
                    grandchild_chunk_info['id'])
                if not grandchild_chunk:
                    continue
                # 回到总入口，递归处理后辈节点
                self._execute_partial(
                    chunk=grandchild_chunk,
                    slow_tasks=slow_tasks,
                    executing_ids=executing_ids,
                    visited_record=visited_record
                )

        # 尝试执行缓执行任务
        if len(executing_ids) == 0:
            self._execute_slow_tasks(slow_tasks)
            slow_tasks.clear()
    
    def _execute_single_chunk(
        self,
        chunk,
        slow_tasks: list,  # 缓执行任务
        executing_ids: list,  # 执行中的任务
        visited_record: list  # 已执行记录
    ):
        """执行完一个 chunk 自身（包含所有可用的依赖数据的组合）"""
        has_been_executed = False
        # 针对循环，不在本执行组内执行，存入缓执行组中，延后执行
        if (chunk.get('loop_entry') == True) and (chunk['id'] in visited_record):
            slow_tasks.append(chunk)
            self.logger.debug(
                f"Put the loop starting chunk '{self._get_chunk_title(chunk)}' into the slow tasks queue for delayed execution")
            return has_been_executed

        # 获取执行chunk的依赖数据（每个手柄可能有多份就绪的数据）
        single_dep_map = self._extract_execution_single_dep_data(chunk)
        while (single_dep_map['is_ready'] and single_dep_map['has_ticket']):
            has_been_executed = True
            # 基于依赖数据快照，执行分组
            self._execute_single_chunk_core(
                chunk=chunk,
                executing_ids=executing_ids,
                visited_record=visited_record,
                single_dep_map=single_dep_map['data']
            )
            # 执行后，收回本次用到的执行票据（仅在自身完了后才执行）
            self._disable_dep_execution_ticket(
                single_dep_map=single_dep_map['data'],
                chunk=chunk
            )
            # 再次更新获取依赖（如没有了，则停止了）
            single_dep_map = self._extract_execution_single_dep_data(chunk)
        return has_been_executed

    def _execute_single_chunk_core(
        self,
        chunk,
        executing_ids: list,  # 执行中的任务
        visited_record: list,  # 已执行记录
        single_dep_map: dict  # 依赖项（已拆组之后的）
    ):
        """根据某一份指定的的依赖数据，执行当前 chunk 自身（不包含下游 chunk 的执行调用）"""
        # 1、执行当前 chunk
        execute_id = uuid.uuid4()
        executing_ids.append(execute_id)
        self.logger.info(
            f"Execute '{self._get_chunk_title(chunk)}'")
        # self.logger.debug("With dependent data: ", single_dep_map)
        exec_value = self._exec_chunk_with_dep_core(chunk, single_dep_map)
        self.breaking_hub.recoder(chunk)  # 更新中断器信息
        visited_record.append(chunk['id'])  # 更新执行记录

        # 2、执行完成后，提取当前执行的结果，尝试将当前执行结果注入到下游的运行依赖插槽上 next_chunk['deps'][]['data_slots'][] = 'xxx'
        for next_info in chunk['next_chunks']:
            next_chunk = self.chunks_map.get(next_info['id'])
            if not next_chunk:
                continue

            # 针对目标 chunk 的目标 handle 的插槽位，注入最新的值（带执行票据的）。（注意如果是条件连接线，需要在条件满足时才更新）
            for next_rel_handle in next_info['handles']:
                source_handle = next_rel_handle['source_handle']
                target_handle = next_rel_handle['handle']
                source_value = exec_value.get(source_handle) if isinstance(
                    exec_value, dict) else exec_value

                # 有条件的情况下，仅在条件满足时，才更新下游节点的数据
                condition_call = next_rel_handle.get('condition')
                if condition_call:
                    judge_res = condition_call(source_value)
                    if judge_res != True:
                        continue

                # 在下一个 chunk 的依赖定义中，找到与当前 chunk 的当前 handle 定义的部分，尝试更新其插槽值依赖
                self.logger.debug(
                    f"Try update chunk '{self._get_chunk_title(next_chunk)}' dep handle '{target_handle}' with value:{source_value}")
                next_chunk_target_dep = find_by_attr(
                    next_chunk['deps'], 'handle', target_handle)
                if next_chunk_target_dep:
                    next_chunk_dep_slots = next_chunk_target_dep['data_slots'] or [
                    ]
                    # 1、首先清空掉之前由当前节点设置，但票据已失效的值
                    next_chunk_target_dep['data_slots'] = next_chunk_dep_slots = [
                        slot for slot in next_chunk_dep_slots if not ((slot['updator'] == chunk['id']) and slot['execution_ticket'] == '')
                    ]

                    # 2、再把本次新的值加入到该下游 chunk 的对应输入点的插槽位中
                    next_chunk_dep_slots.append(
                        create_new_chunk_slot_with_val(chunk['id'], source_value))

        # 任务执行完后，清理执行中的状态
        executing_ids.remove(execute_id)

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
    
    def _exec_chunk_with_dep_core(self, chunk, specified_deps = {}):
        """ 执行任务（执行到此处的都是上游数据已就绪了的） """
        # 简化参数
        deps_dict = {}
        for dep_handle in specified_deps:
            deps_dict[dep_handle] = specified_deps[dep_handle]['value']

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
    
    def _extract_execution_single_dep_data(self, chunk):
        """实时获取某个 chunk 的一组全量可执行数据（如没有，则返回 None）"""
        deps = chunk.get('deps')
        if not deps or len(deps) == 0:
            return {"is_ready": True, "data": None, "has_ticket": True}
        single_dep_map = {}
        exist_exec_ticket = False

        for dep in deps:
            slots = dep['data_slots'] or []
            handle_name = dep['handle']
            # 暂存的就绪的数据（循环中会不停更新，后头的会覆盖前头的），注意，就绪的数据也有可能就是 None，所以 None 不代表没有就绪数据
            tmp_ready_slot = None
            # 是否有就绪的值
            has_ready_value = False

            for slot in slots:
                # 找到就绪的数据
                if slot['is_ready']:
                    has_ready_value = True
                    # 先暂存就绪的数据作为临时数据（后面的会覆盖前头的）
                    tmp_ready_slot = slot

                    # 如果目前全局还没遇到过有票据，且当前为有票据的情况，则作为本次执行的消耗票据
                    if slot['execution_ticket'] and not exist_exec_ticket:
                        exist_exec_ticket = True
                        single_dep_map[handle_name] = slot
                        break

            # 如果跑完所有，还是没设置值（可能没有就绪的数据，或者就绪的数据都是有票据的），需要从就绪的数据中强行取一个作为本次的值
            if (handle_name not in single_dep_map) and has_ready_value:
                single_dep_map[handle_name] = tmp_ready_slot

            # 如果本轮跑完都没有设置值，则标识该 handle 数据未就绪，直接返回
            if handle_name not in single_dep_map:
                return {"is_ready": False, "data": None, "has_ticket": exist_exec_ticket}

        return {"is_ready": True, "data": single_dep_map, "has_ticket": exist_exec_ticket}

    def _disable_dep_execution_ticket(self, single_dep_map, chunk):
        """销毁chunk对应的依赖执行票据（一般在执行结束后操作）"""
        for dep_handle in single_dep_map:
            # 找到被执行的 id
            effect_id = single_dep_map[dep_handle]['id']
            for dep in chunk['deps']:
                slots = dep['data_slots'] or []
                for slot in slots:
                    # 将当前 chunk 中对应手柄的数据项中的对应目标数据的执行票据收回
                    if slot['id'] == effect_id:
                        disable_chunk_dep_ticket(slot)

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
                    data_slots = dep['data_slots']
                    if len(data_slots):
                        for i in range(len(data_slots) - 1, -1, -1):
                            data_slot = data_slots[i]
                            # 如果当前的输入句柄是受上游影响的，则清理掉
                            if (dep['handle'] in effect_handles) and (data_slot['updator'] == '' or data_slot['updator'] == chunk['id']):
                                del data_slots[i]
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
