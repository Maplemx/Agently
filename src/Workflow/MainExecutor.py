import logging
from .utils.logger import get_default_logger
from .lib.BreakingHub import BreakingHub
from .lib.Store import Store

class MainExecutor:
    def __init__(self, settings={}):
        self.is_running = True
        self.running_status = 'idle'
        self.settings = settings
        self.max_execution_limit = (settings or {}).get('max_execution_limit') or 10
        # 实时各节点输入点的数据（仅保留最新的执行结果）
        self.runtime_chunk_data = {}
        self.breaking_hub = BreakingHub(
            breaking_handler = self._handle_breaking,
            max_execution_limit=self.max_execution_limit
        )
        self.store = Store()
        self.logger = settings.get('logger', get_default_logger('Workflow', settings.get('logger_level', logging.INFO)))
        # 已注册的执行器类型
        self.registed_executors = {}

    def startup(self, chunks: list):
        self._reset_temp_status()
        self.running_status = 'start'
        self._exec_tree(chunks)
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
        # 运行时过程中缓存的结果数据
        self.runtime_chunk_data = {}
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

    def _exec_chunk(self, chunk):
        """
        执行任务（执行到此处的都是上游数据已就绪了的）
        """
        # 提取出上游依赖的值(每个桩位仅取一个，如果遇到一个桩位有多个的值的情况，取最新执行的结果)
        deps_temp_res = {}
        for dep in chunk['deps']:
            # 桩位名
            handler_name = dep['target_handler']
            dep_data = self._get_dep_data(dep)
            if dep_data['accessible']:
                new_res_count = self.breaking_hub.get_counts(dep)
                # 未取过值，或者有更新的值时，存储结果
                if handler_name not in deps_temp_res or new_res_count >= deps_temp_res[handler_name]['value_count']:
                    deps_temp_res[handler_name] = {
                        # 取对应的依赖的值
                        "value": dep_data['partial_data'],
                        # 暂存数据
                        "value_count": self.breaking_hub.get_counts(dep),
                        "handle_name": handler_name
                    }
        # 简化参数
        deps_dict = {}
        for handle_name in deps_temp_res:
            deps_dict[handle_name] = deps_temp_res[handle_name]['value']
        chunk_title = chunk["data"]["title"] or 'Unknow chunk'

        # 交给执行器执行
        executor_type = chunk['data']['type']
        chunk_executor = self._get_chunk_executor(executor_type) or chunk.get('executor')
        exec_res = None
        try:
            exec_res = chunk_executor(deps_dict, self.store)
        except Exception as e:
            self.logger.error(f"Node Execution Exception: '{chunk_title}'({chunk['id']}) {e}")
            # 主动中断执行
            raise Exception(e)

        # 存储数据
        self.runtime_chunk_data[chunk['id']] = {
            'type': executor_type,
            'value': exec_res
        }

    def _check_dep_ready(self, chunk):
        """
        监测上游依赖是否就绪
        """
        deps = chunk.get('deps', [])
        if len(deps) == 0:
            return True
        dep_handlers = {}
        for dep in deps:
            # 记录桩点位
            if dep['target_handler'] not in dep_handlers:
                dep_handlers[dep['target_handler']] = False
            # 判断数据是否就绪： 1、节点已有运行结果了；2、对应的连接点有设置初始默认值（default 字段，可为值或函数）
            dep_data = self._get_dep_data(dep)
            if dep_data['accessible']:
                dep_handlers[dep['target_handler']] = True
        # 判断数据是否就绪
        for dep_status in dep_handlers:
            if dep_handlers[dep_status] == False:
                return False
        return True

    def _check_branch_access(self, chunk):
        """
        判断当前chunk分支是否可执行（当父级为判断，如条件不符合则中断）
        """
        deps = chunk.get('deps', [])
        if len(deps) == 0:
            return True
        dep_handlers = {}
        for dep in deps:
            # 如果数据未就绪，表示数据依赖使用的是另外的分组逻辑
            if dep['id'] not in self.runtime_chunk_data:
                continue
            condition_call = dep.get('condition') or None
            # 无条件，直接为通路
            if not condition_call:
                continue
            
            """条件判断"""
            # 记录桩点位
            if dep['target_handler'] not in dep_handlers:
                dep_handlers[dep['target_handler']] = False
            
            # 判断结果
            dep_data = self.runtime_chunk_data[dep['id']].get(
                'value', {}).get(dep['handler'])

            judge_res = condition_call(dep_data or None)

            # 如果判断结果为 True，则更新该桩位的状态为 True
            if judge_res == True:
                dep_handlers[dep['target_handler']] = True

        # 判断所有桩位，看是否存在都为 False 的情况（此时分支中断）
        for dep_status in dep_handlers:
            if dep_handlers[dep_status] == False:
                return False
        return True

    def _get_dep_data(self, dep: dict):
        """
        根据 dep 描述，获取dep 数据
        """
        # 优先从运行时中取
        if dep['id'] in self.runtime_chunk_data:
            chunk_value = (self.runtime_chunk_data[dep['id']].get('value') or {})
            return {
                "accessible": True,
                # 如果不是 dict，则直接作为句柄值
                "partial_data": chunk_value.get(dep['handler']) if isinstance(chunk_value, dict) else chunk_value,
                "refer": 'runtime'
            }
        # 运行时中没有则尝试从定义中看是否有设置默认值
        elif dep.get('default_data') != None:
            default_dep_data = dep.get('default_data')
            if callable(default_dep_data):
                default_dep_data = default_dep_data()
            return {
                "accessible": True,
                "partial_data": default_dep_data,
                "refer": 'default'
            }
        
        return { "accessible": False, "partial_data": None, "refer": None }
    
    def _exec_tree(self, chunks: list):
        """
        执行树（按广度优先顺序执行）
        """
        if not chunks:
            return

        queue = chunks.copy()

        while queue:
            chunk = queue.pop(0)
            # 判断当前节点是否为 Loop 节点，如果是，则重新把循环的起点节点作为本次的执行节点
            if chunk['point_type'] == 'loop':
                chunk = self._find_loop_start_chunk(chunks, chunk)
                if not chunk:
                    continue

            # 非循环尝试执行
            exec_status = self._try_exec_chunk(chunk)
            if exec_status:
                queue.extend(chunk.get("branches", []))
    
    def _try_exec_chunk(self, chunk):
        """
        尝试执行单个 chunk(包括前置的各种检测)
        """
        # 校验上游依赖是否就绪
        if not self._check_dep_ready(chunk):
            self.logger.info(f"'{self._get_chunk_title(chunk)}' dependencies not ready.")
            return False

        # 校验分支是否可执行（例如条件判断未满足，分支不执行）
        if not self._check_branch_access(chunk):
            self.logger.info(
                f"'{self._get_chunk_title(chunk)}' conditions not met")
            return False
        # 执行当前 chunk
        self.logger.info(f"Execute '{self._get_chunk_title(chunk)}'")
        # 1、尝试清空当前节点及下属分支节点
        self._chunks_clean_walker(chunk)
        # 2、开始执行
        self._exec_chunk(chunk)
        # 记录执行
        self.breaking_hub.recoder(chunk)
        return True
    
    def _find_loop_start_chunk(self, chunks: list, loop_chunk):
        """
        查找循环启动节点（深度优先找所在路劲的）
        """
        def deep_walker(chunks, paths):
            for chunk in chunks:
                if chunk != loop_chunk:
                    paths.append(chunk)
                    if chunk.get('branches'):
                        res = deep_walker(chunk.get('branches'), paths)
                        if res == True:
                            return True
                else:
                    return True
            return False
        
        visited_paths = []
        found_target = deep_walker(chunks, visited_paths)

        if found_target:
            for chunk in reversed(visited_paths):
                if chunk['id'] == loop_chunk['id']:
                    return chunk
        return None

    def _chunks_clean_walker(self, chunk):
        """
        尝试对某个节点以下的分支做一轮清理工作
        """
        # 判断当前节点是否为 Loop 节点
        if chunk['point_type'] == 'loop':
            return
        
        # 执行清理工作
        # 1、清理下级分支的失效数据
        if chunk['id'] in self.runtime_chunk_data:
            del self.runtime_chunk_data[chunk['id']]

        # 然后再执行分支
        for branch_chunk in chunk['branches']:
            self._chunks_clean_walker(branch_chunk)
    
    def _get_chunk_title(self, chunk):
        return chunk["data"]["title"] or f'chunk-{chunk["data"]["id"]}' or 'Unknow chunk'

    def _handle_breaking(self, chunk, type):
        """
        处理中断
        """
        self.logger.error(
            f"Exceeded maximum execution limit: {self._get_chunk_title(chunk)}")
        # 中断之前处理相关逻辑
        # 主动中断执行
        raise Exception(
            f"Exceeded maximum execution limit: {self._get_chunk_title(chunk)}")
