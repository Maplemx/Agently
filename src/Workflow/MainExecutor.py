import logging
from .executors.UnknowExecutor import UnknowExecutor
from .utils.logger import get_default_logger
from .lib.BreakingHub import BreakingHub
from .lib.constants import EXECUTOR_TYPE_JUDGE, EXECUTOR_TYPE_END
from .lib.ChunkExecutorABC import ChunkExecutorABC
from .lib.Memory import Memory

class MainExecutor:
    def __init__(self, handler, settings={}):
        self.is_running = True
        self.running_status = 'idle'
        self.handler = handler
        self.settings = settings
        # 实时各节点输入点的数据（仅保留最新的执行结果）
        self.runtime_chunk_data = {}
        self.breaking_hub = BreakingHub(self._handle_breaking, 5)
        self.memory = Memory({
            # 用户输入记录
            'global_user_inputs': []
        })
        self.inputs = []
        self.UnknowExecutor = settings.get('UnknowExecutor', UnknowExecutor)
        self.logger = settings.get('logger', get_default_logger('Workflow', settings.get('logger_level', logging.INFO)))
        # 已注册的执行器类型
        self.registed_executors = {}
        # 判断类型的执行器
        self.judge_executor_types = settings.get('judge_types', [EXECUTOR_TYPE_JUDGE])

    def startup(self, chunks: list):
        self._reset_temp_status()
        self.running_status = 'start'
        for chunk in chunks:
            self._chunks_walker(chunk, [])
        if self.running_status != 'finished':
            self._handle_not_finished()

    def regist_executor(self, name: str, Executor: ChunkExecutorABC):
        """
        注册执行器，传入执行器的名称及 Class（要求为 ChunkExecutorABC 的实现）
        """
        self.registed_executors[name] = Executor

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

    def _get_chunk_executor_class(self, name: str):
        """
        根据名称获取执行器的 Class
        """
        return self.registed_executors.get(name, self.UnknowExecutor)

    def _reset_temp_status(self):
        """
        重置临时状态
        """
        self.running_status = 'idle'
        # 运行时过程中缓存的结果数据
        self.runtime_chunk_data = {}
        # 中断处理
        self.breaking_hub = BreakingHub(self._handle_breaking, 5)

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
            # 处理数据
            if dep['id'] in self.runtime_chunk_data:
                dep_res = self.runtime_chunk_data[dep['id']]
                new_res_count = self.breaking_hub.get_counts(dep)
                # 未取过值，或者有更新的值时，存储结果
                if handler_name not in deps_temp_res or new_res_count >= deps_temp_res[handler_name]['value_count']:
                    deps_temp_res[handler_name] = {
                        # 暂存执行结果
                        "full_value": dep_res['value'],
                        # 取对应的依赖的值
                        "value": dep_res['value'] if (dep['handler'] == 'output' or dep['handler'] is None) else dep_res['value'][dep['handler']],
                        # 暂存数据
                        "value_count": self.breaking_hub.get_counts(dep),
                        "handle_name": handler_name
                    }
        # 简化参数
        deps_dict = {}
        for handle_name in deps_temp_res:
            deps_dict[handle_name] = deps_temp_res[handle_name]['value']
        chunk_title = chunk["data"]["title"]

        # 交给执行器执行
        executor_type = chunk['data']['type']
        ChunkExecutor = self._get_chunk_executor_class(executor_type)
        chunkExecutor = ChunkExecutor(chunk, self)
        exec_res = chunkExecutor.exec(deps_dict)
        # 判断执行结果
        if exec_res['status'] == 'error':
            error_msg = exec_res.get('error_msg', 'Execution Error')
            # 主动中断执行
            raise Exception(
                f"Node Execution Exception: '{chunk_title}'({chunk['id']}) {error_msg}")
        # 存储数据
        self.runtime_chunk_data[chunk['id']] = {
            'type': executor_type,
            'value': exec_res.get('dataset')
        }
        # 判断是否执行结束
        if chunkExecutor.type == EXECUTOR_TYPE_END:
            self._handle_finished(exec_res.get('dataset'))

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
            # 判断数据是否就绪
            if dep['id'] in self.runtime_chunk_data:
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
            res = self.runtime_chunk_data[dep['id']]
            # 针对判断的场景，取判断结果来路由
            if res['type'] in self.judge_executor_types:
                # 记录桩点位
                if dep['target_handler'] not in dep_handlers:
                    dep_handlers[dep['target_handler']] = False
                # 判断结果
                judge_res = res.get('value', {})
                # 如果判断结果为 True，则更新该桩位的状态为 True
                if judge_res.get(dep['handler'], False) == True:
                    dep_handlers[dep['target_handler']] = True
        # 判断所有桩位，看是否存在都为 False 的情况（此时分支中断）
        for dep_status in dep_handlers:
            if dep_handlers[dep_status] == False:
                return False
        return True

    def _chunks_walker(self, chunk, paths = []):
        """
        执行整个 flow
        """
        # 判断当前节点是否为 Loop 节点，如果是，则沿着父级路径追溯，重新跳转到对应的节点位置
        if chunk['point_type'] == 'loop':
            for index, prev_chunk in enumerate(reversed(paths)):
                if prev_chunk['id'] == chunk['id']:
                    target_range = len(paths) - index
                    return self._chunks_walker(prev_chunk, paths[0:target_range - 1] if target_range > 0 else [])
            return

        # 校验上游依赖是否就绪
        if not self._check_dep_ready(chunk):
            self.logger.info(f"'{chunk['data']['title']}' dependencies not ready.")
            return

        # 校验分支是否可执行（例如条件判断未满足，分支不执行）
        if not self._check_branch_access(chunk):
            self.logger.info(
                f"'{chunk['data']['title']}' conditions not met")
            return
        # 执行当前 chunk
        self.logger.info(f"Execute '{chunk['data']['title']}'")
        # 1、尝试清空当前节点及下属分支节点
        self._chunks_clean_walker(chunk)
        # 2、开始执行
        self._exec_chunk(chunk)
        # 记录执行
        self.breaking_hub.recoder(chunk)

        # 再执行分支 chunk
        for branch_chunk in chunk['branches']:
            new_paths = paths.copy()
            new_paths.append(chunk)
            self._chunks_walker(branch_chunk, new_paths)
    
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

    def _handle_finished(self, res):
        self.running_status = 'finished'
        self.logger.info("[Finished]")
        self.handler("response", res)

    def _handle_not_finished(self):
        self.handler("error", 'Workflow not yet completed')

    def _handle_breaking(self, chunk, type):
        """
        处理中断
        """
        self.logger.error(
            f"Exceeded maximum execution limit: {chunk['data']['title'] if 'title' in chunk['data'] else chunk['id']}")
        # 中断之前处理相关逻辑
        # 主动中断执行
        raise Exception(
            f"Exceeded maximum execution limit: {chunk['data']['title'] if 'title' in chunk['data'] else chunk['id']}")
