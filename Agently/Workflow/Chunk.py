import uuid
import copy
import inspect
from .utils.find import has_target_by_attr
from .lib.constants import DEFAULT_OUTPUT_HANDLE_VALUE, DEFAULT_INPUT_HANDLE_VALUE, EXECUTOR_TYPE_NORMAL, EXECUTOR_TYPE_START, EXECUTOR_TYPE_END, EXECUTOR_TYPE_LOOP

# 特殊的内置的 chunk 类型
SPECIAL_CHUNK_TYPES = [
    EXECUTOR_TYPE_START,
    EXECUTOR_TYPE_END,
    EXECUTOR_TYPE_LOOP
]

class SchemaChunk:
    """
    Workflow Schema 中的单个 chunk 结构，用于辅助提供操作的 API，实际运行时，提供 chunk 描述参数交给 MainExecutor 执行。
    注意，仅当connect_to/loop 调用时，才会实质创建运行时相关参数，否则仅仅是参数挂载
    """

    def __init__(self, workflow_schema = None, type = EXECUTOR_TYPE_NORMAL, executor: callable = None, **chunk_desc):
        """
        必选参数 executor，或 type 为 'Start'
        """
        # 校验必填字段(要么 type 为特殊类型，否则必须包含 executor)
        if not type or (type not in SPECIAL_CHUNK_TYPES):
            if not executor:
                raise ValueError("Missing required key: 'executor'")

        self.chunk = {
            'id': chunk_desc.get('id', str(uuid.uuid4())),
            'title': chunk_desc.get('title'),
            'type': type or EXECUTOR_TYPE_NORMAL,
            'executor': executor,
            'handles': self._fix_handles(chunk_desc.get('handles')),
            # 连接条件（默认无条件连通）
            'connect_condition': chunk_desc.get('connect_condition') or None,
            # 连接条件的描述（if/elif，condition_id 信息等）
            'connect_condition_detail': chunk_desc.get('connect_condition_detail') or None,
            # 当前激活的待连接的 handle 名
            'active_handle': chunk_desc.get('active_handle') or None,
            # 扩展信息
            'extra_info': chunk_desc.get('extra_info') or {}
        }

        self.workflow_schema = workflow_schema

        # 调用链上，分支路径
        self.branch_chunk_stack = chunk_desc.get('branch_chunk_stack') or []
    
    def handle(self, name: str) -> 'SchemaChunk':
        """Chunk 的连接点，注意 handle 可能在此时还未注册，在其进行连接操作时，会自动帮其注册"""
        # 创建影子 chunk，逻辑分支继续延续
        shadow_chunk = self.create_shadow_chunk(persist_branch_chain=True)
        shadow_chunk.set_active_handle(name)
        return shadow_chunk
    
    def if_condition(self, condition: callable = None) -> 'SchemaChunk':
        """
        按条件连接
        """
        # 创建影子 chunk
        shadow_chunk = self.create_shadow_chunk(persist_branch_chain=True)
        # 逻辑分支在原有基础上，追加当前 chunk
        shadow_chunk.branch_chunk_stack.append(shadow_chunk)
        # 设置条件参数和辅助信息
        shadow_chunk.set_connect_condition(
            condition = condition,
            condition_detail = {
                # condition id
                "id": f"cid-{str(uuid.uuid4())}",
                "type": "if"
            }
        )
        return shadow_chunk

    def else_condition(self) -> 'SchemaChunk':
        """
        按当前条件的反条件连接（特别注意，else_condition 作用的 chunk 为往前追溯的最近一个 if_condition 作用的 chunk，两是同一个，两是成套存在的）
        """
        # Step1. 从当前 chunk 的 branch_chunk_stack 从后往前找，找到最近一个 if_condition 的 'root' chunk
        branch_chunk_stack = self.branch_chunk_stack.copy()
        cursor_chunk = branch_chunk_stack.pop() if len(branch_chunk_stack) else None
        # 本次 else 条件的root chunk（即 if 的那个 chunk）
        condition_root_chunk: 'SchemaChunk' = None
        while cursor_chunk:
            cursor_chunk_params = cursor_chunk.chunk
            if cursor_chunk_params.get('connect_condition') and (cursor_chunk_params.get('connect_condition_detail') or {}).get('type') == 'if':
                condition_root_chunk = cursor_chunk
                break
            cursor_chunk = branch_chunk_stack.pop() if len(branch_chunk_stack) else None
        
        if not condition_root_chunk:
            raise ValueError(
                f"The `else_condition` method must be called after the `if_condition` method.")

        # Step2. 基于 condition_root_chunk 做进一步的连接和更新操作
        # 2.1 生成 else_fn
        current_condition = condition_root_chunk.chunk.get('connect_condition')
        if not current_condition:
            def current_condition(values, store):
                return True
        def else_condition_func(values, store):
            res = not current_condition(values, store)
            return res

        # 2.2 进行条件连接
        # 在 shadow_root_chunk 上操作，重构 branch_chain 剩下的即剔除了主 if 的路径继续保留
        shadow_root_chunk = condition_root_chunk.create_shadow_chunk(persist_branch_chain=False)
        shadow_root_chunk.branch_chunk_stack = branch_chunk_stack.copy()
        # 设置条件链接信息
        shadow_root_chunk.set_connect_condition(
            condition = else_condition_func,
            condition_detail = {
                "id": (condition_root_chunk.chunk.get('connect_condition_detail') or {}).get('id') or f"cid-{str(uuid.uuid4())}",
                "type": "elif"
            }
        )
        return shadow_root_chunk

    def connect_to(self, chunk: 'SchemaChunk') -> 'SchemaChunk':
        if isinstance(chunk, str):
            chunks = self.workflow_schema.workflow.chunks
            chunk_info_list = chunk.split(".")
            if len(chunk_info_list) < 2:
                chunk_id = chunk_info_list[0]
                if chunk_id not in chunks:
                    raise Exception(f"Can not find '{ chunk_id }' in workflow.chunks.")
                return self._connect_to(chunks[chunk_id])
            else:
                chunk_id = chunk_info_list[0]
                handle_name = chunk_info_list[1]
                if chunk_id not in chunks:
                    raise Exception(f"Can not find '{ chunk_id }' in workflow.chunks.")
                return self._connect_to(chunks[chunk_id].handle(handle_name))
        else:
            return self._connect_to(chunk)

    def _connect_to(self, chunk: 'SchemaChunk') -> 'SchemaChunk':
        """
        连接到指定个 Chunk 节点，支持传入 create_chunk 创建好的实例，也支持传入 chunk dict
        """
        # 如果传入的是一个 dict 类型，自动进行实例化再连接
        target_chunk = self.workflow_schema.create_chunk(**chunk) if isinstance(chunk, dict) else chunk
        if not isinstance(target_chunk, SchemaChunk):
            raise ValueError(f"The 'chunk' parameter to 'connect_to' is invalid.")

        # 检测 chunk 是否在当前 workflow 中有注册
        if not self.workflow_schema.get_chunk(target_chunk.chunk['id']):
            raise ValueError(f"The two chunk are not mounted under the same 'workflow'.")
        
        # 连接两 chunk
        self.workflow_schema.connect_chunk(
            self.chunk['id'],
            target_chunk.chunk['id'],
            self.chunk.get('active_handle') or DEFAULT_OUTPUT_HANDLE_VALUE,
            target_chunk.chunk.get('active_handle') or DEFAULT_INPUT_HANDLE_VALUE,
            self.chunk.get('connect_condition') or None,
            self.chunk.get('connect_condition_detail') or None,
        )
        # chain 往前递进
        target_chunk_shadow = target_chunk.create_shadow_chunk(persist_branch_chain=False)
        target_chunk_shadow.branch_chunk_stack = self.branch_chunk_stack.copy()
        target_chunk_shadow.set_active_handle()
        return target_chunk_shadow

    def loop_with(self, sub_workflow)-> 'SchemaChunk':
        """遍历逐项处理，支持传入子 workflow/处理方法 作为处理逻辑"""
        async def loop_executor(inputs, store):
            input_val = inputs.get(DEFAULT_INPUT_HANDLE_VALUE)
            all_result = []
            if isinstance(input_val, list):
                for val in input_val:
                    all_result.append(await loop_unit_core(unit_val=val, store=store))
            elif isinstance(input_val, dict):
                for key, value in input_val.items():
                    all_result.append(await loop_unit_core(unit_val={
                        "key": key,
                        "value": value
                    }, store=store))
            elif isinstance(input_val, int):
                for i in range(input_val):
                    all_result.append(await loop_unit_core(unit_val=i, store=store))
            return all_result

        async def loop_unit_core(unit_val, store):
            if inspect.iscoroutinefunction(sub_workflow):
                return await sub_workflow(unit_val, store)
            elif inspect.isfunction(sub_workflow):
                return sub_workflow(unit_val, store)
            else:
                return await sub_workflow.start_async(unit_val)

        is_function = inspect.isfunction(sub_workflow) or inspect.iscoroutinefunction(sub_workflow)
        # 这里是新的 chunk，需要走 Schema 的 create 方法挂载
        loop_chunk = self.workflow_schema.create_chunk(
            type=EXECUTOR_TYPE_LOOP,
            executor=loop_executor,
            extra_info={
                # loop 的相关信息
                "loop_info": {
                    "type": 'function' if is_function else 'workflow',
                    "detail": sub_workflow.__name__ if is_function else sub_workflow.schema.compile()
                }
            }
        )
        return self.connect_to(loop_chunk)
    
    def get_raw_schema(self):
        return copy.deepcopy(self.chunk)
    
    def set_active_handle(self, name: str = None):
        """设置激活的连接点，连接时会默认连接到该点上"""
        self.chunk['active_handle'] = name
    
    def set_connect_condition(self, condition: callable = None, condition_detail: dict = None):
        """设置连接的条件"""
        self.chunk['connect_condition'] = condition
        self.chunk['connect_condition_detail'] = condition_detail
    
    def has_handle(self, name: str, from_inputs = True) -> bool:
        """判断连接手柄是否存在"""
        search_range = self.chunk.get('handles').get('inputs' if from_inputs else 'outputs', [])
        return has_target_by_attr(search_range, 'handle', name)
    
    def create_shadow_chunk(self, persist_branch_chain=False):
        """获取到当前 chunk 的拷贝份（不干扰 chunk 自身运算逻辑），persist_branch_chain 为是否保留逻辑分支链"""
        shadow_chunk = SchemaChunk(
            workflow_schema=self.workflow_schema,
            **self.get_raw_schema()
        )
        if persist_branch_chain:
            shadow_chunk.branch_chunk_stack = self.branch_chunk_stack.copy()
        return shadow_chunk

    def _fix_handles(self, custom_handles):
        """修正用户传入的 handles 配置格式"""
        # 处理默认 handle
        handles = custom_handles or { 'inputs': [], 'outputs': [] }
        if 'inputs' not in handles:
            handles['inputs'] = []
        if 'outputs' not in handles:
            handles['outputs'] = []

        # 处理 handle 点简写的情况（如：{ "inputs": ['topic', 'type'], "outputs": [{"handle": "output"}] } 中的 inputs 的定义方式）
        def fix_handle_core(handle_list):
            if not handle_list:
                return
            if handle_list and len(handle_list):
                for idx, handle in enumerate(handle_list):
                    if isinstance(handle, str):
                        handle_list[idx] = { "handle": handle }

        fix_handle_core(handles['inputs'])
        fix_handle_core(handles['outputs'])
        return handles
