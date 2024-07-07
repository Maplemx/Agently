import uuid
import copy
import inspect
from .utils.find import has_target_by_attr
from .executors.generater.loop import use_loop_executor
from .lib.constants import DEFAULT_OUTPUT_HANDLE_VALUE, DEFAULT_INPUT_HANDLE_VALUE, EXECUTOR_TYPE_NORMAL, EXECUTOR_TYPE_START, EXECUTOR_TYPE_END, EXECUTOR_TYPE_LOOP, EXECUTOR_TYPE_CONDITION, BUILT_IN_EXECUTOR_TYPES

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
        if not type or (type not in BUILT_IN_EXECUTOR_TYPES):
            if not executor:
                raise ValueError("Missing required key: 'executor'")

        """ chunk 运行时参数 """
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

        """ api 支撑性参数（主要用于支撑 API 表达，与具体运行时无关），创建拷贝份时需要注意处理"""
        self.condition_chunk_path = chunk_desc.get('condition_chunk_path', [])

        self.workflow_schema = workflow_schema
    
    def handle(self, name: str) -> 'SchemaChunk':
        """Chunk 的连接点，注意 handle 可能在此时还未注册，在其进行连接操作时，会自动帮其注册"""
        # 创建影子 chunk，逻辑分支继续延续
        shadow_chunk = self.create_shadow_chunk()
        shadow_chunk.set_active_handle(name)
        return shadow_chunk

    def if_condition(self, condition: callable = None) -> 'SchemaChunk':
        """条件判断"""
        condition_signal_id = str(uuid.uuid4())
        # 创建新的 condition chunk，需要走 Schema 的 create 方法挂载
        condition_chunk = self._create_rel_chunk(
            type=EXECUTOR_TYPE_CONDITION,
            title="Condition",
            extra_info={
                # condition 的相关信息
                "condition_info": {
                    # 常规条件
                    "conditions": [{
                        # 命中时的结果符号
                        "condition_signal": condition_signal_id,
                        "condition": condition
                    }],
                    "else_condition": {
                        # 命中时的结果符号
                        "condition_signal": str(uuid.uuid4())
                    }
                }
            }
        )
        new_path_item = {
            'root': self,
            'condition': condition_chunk
        }
        # 以 condition_chunk 为起点，追加上条件路径信息（下游条件逻辑都可基于此判断处理）
        condition_chunk.condition_chunk_path.append(new_path_item)
        # 把上游chunk连接到主判断节点（仅 if 时操作一次即可，后续皆为连接到condition chunk）
        connected_handle = self.connect_to(condition_chunk)
        # 新连接的第一个 chunk，也需要补充本次的条件路径
        connected_handle.condition_chunk_path.append(new_path_item)
        # 设置条件参数和辅助信息
        connected_handle.set_connect_condition(
            condition=lambda runtime_signal, storage: runtime_signal == condition_signal_id,
            condition_detail={
                # condition id
                "id": f"cid-{str(uuid.uuid4())}",
                "type": "if"
            }
        )
        return connected_handle
    
    def elif_condition(self, condition: callable = None) -> 'SchemaChunk':
        """elif 条件判断"""
        # Step1. 从当前 chunk 中，读取所属的条件 chunk id 信息
        condition_path = self.condition_chunk_path
        condition_path_item = condition_path[-1] if condition_path else None
        if not condition_path_item:
            raise ValueError(
                f"The `elif_condition` method must be called after the `if_condition` method.")

        condition_chunk: 'SchemaChunk' = condition_path_item.get('condition')
        # Step2. 基于 condition_chunk 做进一步的连接和更新操作
        # 2.1 生成 elif_fn
        condition_signal_id = str(uuid.uuid4())
        condition_info = (condition_chunk.chunk.get('extra_info') or {}).get('condition_info') or {}
        # 追加条件信号
        condition_info.get('conditions', []).append({
            # 命中时的结果符号
            "condition_signal": condition_signal_id,
            "condition": condition
        })

        # 2.2 进行条件连接
        # 设置条件链接信息
        condition_chunk.set_connect_condition(
            condition=lambda runtime_signal, storage: runtime_signal == condition_signal_id,
            condition_detail={
                "id": (condition_chunk.chunk.get('connect_condition_detail') or {}).get('id') or f"cid-{str(uuid.uuid4())}",
                "type": "elif"
            }
        )
        shadow_root_chunk = condition_chunk.create_shadow_chunk()
        return shadow_root_chunk
    
    def else_condition(self) -> 'SchemaChunk':
        """
        按当前条件的反条件连接（特别注意，else_condition 作用的 chunk 为往前追溯的最近一个 if_condition 作用的 chunk，两是同一个，两是成套存在的）
        """
        # Step1. 从当前 chunk 中，读取所属的条件 chunk id 信息
        condition_path = self.condition_chunk_path
        condition_path_item = condition_path[-1] if condition_path else None
        if not condition_path_item:
            raise ValueError(
                f"The `else_condition` method must be called after the `if_condition` method.")

        condition_chunk: 'SchemaChunk' = condition_path_item.get('condition')
        # Step2. 基于 condition_chunk 做进一步的连接和更新操作
        # 2.1 生成 else_fn
        condition_info = (condition_chunk.chunk.get('extra_info') or {}).get('condition_info') or {}
        else_signal = (condition_info.get('else_condition') or {}).get('condition_signal') or str(uuid.uuid4())

        # 2.2 进行条件连接
        # 在 shadow_root_chunk 上操作，支撑参数剔除当前所在条件 chunk 后继续保留
        shadow_root_chunk = condition_chunk.create_shadow_chunk()
        # 设置条件链接信息
        shadow_root_chunk.set_connect_condition(
            condition=lambda runtime_signal, storage: runtime_signal == else_signal,
            condition_detail={
                "id": (condition_chunk.chunk.get('connect_condition_detail') or {}).get('id') or f"cid-{str(uuid.uuid4())}",
                "type": "else"
            }
        )
        return shadow_root_chunk
    
    def end_condition(self) -> 'SchemaChunk':
        """终止当前所在的if，回退到当次 if 前的 chunk"""
        # Step1. 从当前 chunk 中，读取所属的条件 chunk id 信息
        condition_path = self.condition_chunk_path
        condition_path_item = condition_path[-1] if condition_path else None
        if not condition_path_item:
            raise ValueError(
                f"The `end_condition` method must be called after the `if_condition` method.")
        # Step2. 回退到本次条件的 root chunk
        return condition_path_item.get('root').create_shadow_chunk()

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
        elif callable(chunk):
            temp_chunk = self.workflow_schema.create_chunk(
                executor=chunk,
                type=EXECUTOR_TYPE_NORMAL,
                title = (
                         f"@{ chunk.__name__ }"
                         if not chunk.__name__ == "<lambda>"
                         else f"lambda-{ str(uuid.uuid4()) }"
                     ),
            )
            return self._connect_to(temp_chunk)
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
        target_chunk_shadow = target_chunk.create_shadow_chunk(persist_supports_data=False)
        # 将目标 chunk 的 condtion 路径与上游 chunk 同频
        target_chunk_shadow.condition_chunk_path = self.condition_chunk_path.copy()
        target_chunk_shadow.set_active_handle()
        return target_chunk_shadow

    def loop_with(self, sub_workflow)-> 'SchemaChunk':
        """遍历逐项处理，支持传入子 workflow/处理方法 作为处理逻辑"""
        is_function = inspect.isfunction(sub_workflow) or inspect.iscoroutinefunction(sub_workflow)
        # 这里是新的 chunk，需要走 Schema 的 create 方法挂载
        loop_chunk = self._create_rel_chunk(
            type=EXECUTOR_TYPE_LOOP,
            title="Loop",
            executor=use_loop_executor(sub_workflow),
            extra_info={
                # loop 的相关信息
                "loop_info": {
                    "type": 'function' if is_function else 'workflow',
                    "detail": sub_workflow.__name__ if is_function else sub_workflow.schema.compile()
                }
            }
        )
        return self.connect_to(loop_chunk)
    
    def get_raw_schema(self, use_origin=False):
        """获取原始的配置"""
        return self.chunk if use_origin else copy.deepcopy(self.chunk)
    
    def set_active_handle(self, name: str = None):
        """设置激活的连接点，连接时会默认连接到该点上"""
        self.chunk['active_handle'] = name
    
    def set_connect_condition(self, condition: callable = None, condition_detail: dict = None):
        """设置连接的条件"""
        self.chunk['connect_condition'] = condition
        self.chunk['connect_condition_detail'] = condition_detail
        return self
    
    def has_handle(self, name: str, from_inputs = True) -> bool:
        """判断连接手柄是否存在"""
        search_range = self.chunk.get('handles').get('inputs' if from_inputs else 'outputs', [])
        return has_target_by_attr(search_range, 'handle', name)
    
    def create_shadow_chunk(self, persist_supports_data=True):
        """获取到当前 chunk 的拷贝份（不干扰 chunk 自身运算逻辑），persist_supports_data 为是否保留支撑参数"""
        shadow_chunk = SchemaChunk(
            workflow_schema=self.workflow_schema,
            **self.get_raw_schema()
        )
        if persist_supports_data:
            shadow_chunk.condition_chunk_path = self.condition_chunk_path.copy()
        return shadow_chunk

    def _create_rel_chunk(self, persist_supports_data=True, **params) -> 'SchemaChunk':
        """在当前 schema 上创建一个新的 chunk """
        if persist_supports_data:
            return self.workflow_schema.create_chunk(
                **params,
                # 运行时支撑参数
                condition_chunk_path=self.condition_chunk_path.copy()
            )
        return self.workflow_schema.create_chunk(**params)

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
