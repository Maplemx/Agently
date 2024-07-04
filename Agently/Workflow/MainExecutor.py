import uuid
import asyncio
import inspect
from ..utils import RuntimeCtx
from .utils.exec_tree import disable_chunk_dep_ticket, create_new_chunk_slot_with_val
from .utils.find import find_by_attr
from .lib.BreakingHub import BreakingHub
from .lib.Store import Store
from .lib.constants import WORKFLOW_START_DATA_HANDLE_NAME, WORKFLOW_END_DATA_HANDLE_NAME, DEFAULT_INPUT_HANDLE_VALUE, DEFAULT_OUTPUT_HANDLE_VALUE, BUILT_IN_EXECUTOR_TYPES, EXECUTOR_TYPE_CONDITION

class MainExecutor:
    def __init__(self, workflow_id, settings: RuntimeCtx, logger):
        # == Step 1. 初始化设定配置 ==
        self.workflow_id = workflow_id
        self.settings = settings
        self.max_execution_limit = self.settings.get('max_execution_limit') or 10
        self.logger = logger
        # == Step 2. 初始化状态配置 ==
        self.running_status = 'idle'
        # 中断器
        self.breaking_hub = BreakingHub(
            breaking_handler = self._handle_breaking,
            max_execution_limit=self.max_execution_limit
        )
        # 运行时数据存储
        self.store = self.settings.get('store') or Store()
        # 运行时系统存储（如存储整个 workflow 的输入输出数据）
        self.sys_store  = self.settings.get('sys_store') or Store()
        # 是否保留执行状态
        self.persist_state = self.settings.get('persist_state') == True
        self.persist_sys_state = self.settings.get('persist_sys_state') == True
        # 已注册的执行器
        self.registed_executors = {}
        # 执行节点字典
        self.chunks_map = {}

    async def start(self, executed_schema: dict, start_data: any = None, *, storage: dict = None):
        self.reset_all_runtime_status()
        # Set Initial Storage
        if storage and not isinstance(storage, dict):
            raise Exception(f"Initial storage can only be a dictionary.\nstorage = { storage }")
        if storage and isinstance(storage, dict):
            self.store.update_by_dict(storage)
        # 尝试灌入初始数据
        self.sys_store.set(WORKFLOW_START_DATA_HANDLE_NAME, start_data)
        self.chunks_map = executed_schema.get('chunk_map') or {}
        self.running_status = 'start'
        await self._execute_main(executed_schema.get('entries') or [])
        self.running_status = 'end'
        return self.sys_store.get(WORKFLOW_END_DATA_HANDLE_NAME) or None

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

    def reset_all_runtime_status(self):
        """重置状态配置"""
        self.running_status = 'idle'
        # 中断器
        self.breaking_hub = BreakingHub(
            breaking_handler=self._handle_breaking,
            max_execution_limit=self.max_execution_limit
        )
        # 运行时数据存储
        if not self.persist_state:
            self.store.remove_all()
        if not self.persist_sys_state:
            self.sys_store.remove_all()
        # 执行节点字典
        self.chunks_map = {}
    
    async def _execute_main(self, entries: list):
        """执行入口"""

        # 1、声明单个执行逻辑（异步）
        async def execute_from_entry(entry):
            slow_tasks = []
            await self._execute_partial(
                entry,
                slow_tasks=slow_tasks,
                executing_ids=[],
                visited_record=[]
            )
            # 如果执行完成后，还有待执行任务，则需手动执行
            if len(slow_tasks) > 0:
                await self._execute_slow_tasks(slow_tasks)

        # 2、收集执行任务
        entry_tasks = [execute_from_entry(entry_chunk) for entry_chunk in entries]

        # 3、最后再统一执行
        await asyncio.gather(*entry_tasks)

    async def _execute_partial(
            self,
            chunk,
            slow_tasks: list, # 缓执行任务
            executing_ids: list, # 执行中的任务
            visited_record: list # 已执行记录
        ):
        """一组分组执行的核心方法"""

        # 1、执行当前 chunk
        has_been_executed = await self._execute_single_chunk(
            chunk=chunk,
            slow_tasks=slow_tasks,
            executing_ids=executing_ids,
            visited_record=visited_record
        )
        # 如果根本未执行过（如无执行票据），直接返回
        if not has_been_executed:
            return

        # 2、执行下游直接子 chunk 自身
        executed_child_chunks = []
        # 2.1 声明执行处理逻辑
        async def execute_child_chunk(next_chunk):
            self.logger.debug(
                f"Try to call next chunk '{self._get_chunk_title(next_chunk)}' from chunk '{self._get_chunk_title(chunk)}'")
            child_executed = await self._execute_single_chunk(
                chunk=next_chunk,
                slow_tasks=slow_tasks,
                executing_ids=executing_ids,
                visited_record=visited_record
            )
            # 成功执行的塞入记录中（用于稍后处理其后续的chunk）
            if child_executed:
                executed_child_chunks.append(next_chunk['id'])

        # 2.2 执行直接子任务
        for next_info in chunk['next_chunks']:
            next_chunk = self.chunks_map.get(next_info['id'])
            if not next_chunk:
                continue

            # 在保持状态正确的前提下执行
            await execute_child_chunk(next_chunk)

        # 3、递归处理已执行了的下游直接子节点的下级节点
        # 3.1 收集直接子节点的待执行的下游任务
        next_child_tasks = []
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
                # 回到总入口，递归处理后辈节点（收集阶段，执行在后头并行执行）
                next_child_tasks.append(
                    self._execute_partial(
                        chunk=grandchild_chunk,
                        slow_tasks=slow_tasks,
                        executing_ids=executing_ids,
                        visited_record=visited_record
                    )
                )

        # 3.2 集中等待后辈任务执行完
        if len(next_child_tasks):
            await asyncio.gather(*next_child_tasks)

        # 4、最后尝试执行缓执行任务（如循环，要在慢于常规任务的执行）
        if len(executing_ids) == 0:
            await self._execute_slow_tasks(slow_tasks)
            slow_tasks.clear()
    
    async def _execute_single_chunk(
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
            await self._execute_single_chunk_core(
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

    async def _execute_single_chunk_core(
        self,
        chunk,
        executing_ids: list,  # 执行中的任务
        visited_record: list,  # 已执行记录
        single_dep_map: dict  # 依赖项（已拆组之后的）
    ):
        """根据某一份指定的的依赖数据，执行当前 chunk 自身（不包含下游 chunk 的执行调用）"""
        # 1、执行当前 chunk
        execute_id = str(uuid.uuid4())
        executing_ids.append(execute_id)
        # self.logger.debug("With dependent data: ", single_dep_map)
        exec_res = await self._exec_chunk_with_dep_core(chunk, single_dep_map)
        exec_value = exec_res['value']
        condition_signal = exec_res['signal']

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
                source_value = None
                # 以下情况直接将完整值注入下游对应的插槽位置（此处的 target_handle）：执行结果为非 dict 类型，或者未定义上游 chunk 的输出句柄(此处的 source_handle)，或其输出句柄为默认全量输出句柄时
                if (not isinstance(exec_value, dict)) or (not source_handle) or (source_handle == DEFAULT_OUTPUT_HANDLE_VALUE):
                    source_value = exec_value
                else:
                    source_value = exec_value.get(source_handle)

                # 有条件的情况下，仅在条件满足时，才更新下游节点的数据
                condition_call = next_rel_handle.get('condition')
                if condition_call:
                    judge_res = condition_call(condition_signal, self.store)
                    connection_status = judge_res == True
                    self.logger.debug(
                        f"The connection status of '{self._get_chunk_title(chunk)}({source_handle})' to '{self._get_chunk_title(next_chunk)}({target_handle})': {connection_status}")
                    if not connection_status:
                        continue

                # 在下一个 chunk 的依赖定义中，找到与当前 chunk 的当前 handle 定义的部分，尝试更新其插槽值依赖
                self.logger.debug(
                    f"Try update chunk '{self._get_chunk_title(next_chunk)}' dep handle '{target_handle}' with value:{source_value}")
                next_chunk_target_dep = find_by_attr(
                    next_chunk['deps'], 'handle', target_handle)
                if next_chunk_target_dep:
                    next_chunk_dep_slots = next_chunk_target_dep['data_slots'] or []
                    # 1、首先清空掉之前由当前节点设置，但票据已失效的值
                    next_chunk_target_dep['data_slots'] = next_chunk_dep_slots = [
                        slot for slot in next_chunk_dep_slots if not ((slot['updator'] == chunk['id']) and slot['execution_ticket'] == '')
                    ]

                    # 2、再把本次新的值加入到该下游 chunk 的对应输入点的插槽位中
                    next_chunk_dep_slots.append(
                        create_new_chunk_slot_with_val(chunk['id'], source_value))

        # 任务执行完后，清理执行中的状态
        executing_ids.remove(execute_id)

    async def _execute_slow_tasks(self, slow_tasks):
        """尝试执行低优任务"""
        if len(slow_tasks) == 0:
            return

        self.logger.debug(f'Try to execute the slow tasks queue(length: {len(slow_tasks)})')
        for chunk in slow_tasks:
            # 先清空下游所有节点数据
            self._chunks_clean_walker(chunk)
            # 再启动执行
            await self._execute_partial(
                chunk,
                slow_tasks=[],
                executing_ids=[],
                visited_record=[]
            )
    
    async def _exec_chunk_with_dep_core(self, chunk, specified_deps = {}):
        """ 执行任务（执行到此处的都是上游数据已就绪了的） """
        # 简化参数
        deps_dict = {}
        for dep_handle in specified_deps:
            deps_dict[dep_handle] = specified_deps[dep_handle]['value']
        
        input_value = deps_dict

        # 激进模式下的特殊处理
        if self.settings.get('mode') == 'aggressive':
            # 如果只有一个数据挂载，且为 default，则直接取出来作为默认值
            all_keys = list(deps_dict.keys())
            if len(all_keys) == 1 and all_keys[0] == DEFAULT_INPUT_HANDLE_VALUE:
                input_value = deps_dict['default']

        # 交给执行器执行
        executor_type = chunk['data']['type']
        chunk_executor = self._get_chunk_executor(executor_type) or chunk.get('executor')
        # 是否内置的执行器（会追加系统信息）
        is_built_in_type = executor_type in BUILT_IN_EXECUTOR_TYPES
        exec_res = None
        if not chunk_executor:
            err_msg = f"Node {executor_type} Error-'{self._get_chunk_title(chunk)}'({chunk['id']}): The 'executor' is required but get 'NoneType'"
            self.logger.error(err_msg)
            # 主动中断执行
            raise Exception(err_msg)
        try:
            self.logger.info(f"Executing chunk '{self._get_chunk_title(chunk)}'")
            # 如果执行器是异步的，采用 await调用
            if inspect.iscoroutinefunction(chunk_executor):
                if is_built_in_type:
                    exec_res = await chunk_executor(input_value, self.store, sys_store=self.sys_store, chunk=chunk)
                else:
                    exec_res = await chunk_executor(input_value, self.store)
            else:
                if is_built_in_type:
                    exec_res = chunk_executor(input_value, self.store, sys_store=self.sys_store, chunk=chunk)
                else:
                    exec_res = chunk_executor(input_value, self.store)
        except Exception as e:
            self.logger.error(f"Node Execution Exception-'{self._get_chunk_title(chunk)}'({chunk['id']}):\n {e}")
            # 主动中断执行
            raise Exception(e)

        exec_value = exec_res
        condition_signal = None
        # 条件节点，拆分为条件信号和执行结果两部分
        if chunk['type'] == EXECUTOR_TYPE_CONDITION:
            exec_value = exec_res.get('values')
            condition_signal = exec_res.get('condition_signal')
        return {
            "value": exec_value,
            "signal": condition_signal
        }
    
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

    def _chunks_clean_walker(self, root_chunk):
        """尝试对某个节点以下的分支做一轮清理工作"""

        visited_record = []
        def clean_core(chunk):
            for next_info in chunk['next_chunks']:
                next_chunk = self.chunks_map.get(next_info['id'])
                if not next_chunk:
                    continue

                # 同一个发起方的清理，只执行一次，避免死循环
                visited_symbol = f"{chunk['id']}-2-{next_chunk['id']}"
                if (visited_symbol in visited_record) or (next_chunk['id'] == root_chunk['id']):
                    continue

                visited_record.append(visited_symbol)
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
