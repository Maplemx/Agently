import uuid
import copy
from typing import TYPE_CHECKING, TypeVar, Type
from ..utils.chunk_helper import deep_copy_simply
from ..utils.find import has_target_by_attr
from ..lib.constants import EXECUTOR_TYPE_NORMAL, BUILT_IN_EXECUTOR_TYPES, DEFAULT_OUTPUT_HANDLE_VALUE, DEFAULT_INPUT_HANDLE_VALUE
from .Condition import ConditionAbility
from .Loop import LoopAbility
from .helper import exposed_interface

if TYPE_CHECKING:
    from ..Schema import Schema

T = TypeVar('T')


class SchemaChunk(ConditionAbility, LoopAbility):
    """
    Workflow Schema 中的单个 chunk 结构，用于辅助提供操作的 API，实际运行时，提供 chunk 描述参数交给 MainExecutor 执行。
    注意，仅当connect_to/loop 调用时，才会实质创建运行时相关参数，否则仅仅是参数挂载
    """

    def __init__(self, workflow_schema: 'Schema' = None, type=EXECUTOR_TYPE_NORMAL, executor: callable = None, **chunk_desc):
        """
        必选参数 executor，或 type 为 'Start'
        """
        # 校验必填字段(要么 type 为特殊类型，否则必须包含 executor)
        if not type or (type not in BUILT_IN_EXECUTOR_TYPES):
            if not executor:
                raise ValueError("Missing required key: 'executor'")

        self.workflow_schema = workflow_schema

        # chunk 运行时参数，每个字段均参与运行过程
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
            # 扩展信息
            'extra_info': chunk_desc.get('extra_info') or {}
        }

        self._pre_command_interceptors = []
        self._post_command_interceptors = []
        # 支撑参数空间
        self.shared_ns = {
            'connection_ns': {
                'active_handle': chunk_desc.get('active_handle', None)
            }
        }
        # 链路信息空间（会在chunk流转到另一个chunk时透传）
        self.shared_chain_ns = {}
        super().__init__()
    
    @exposed_interface(type='attr')
    def handle(self, name: str) -> 'SchemaChunk':
        """Chunk 的连接点，注意 handle 可能在此时还未注册，在其进行连接操作时，会自动帮其注册"""
        # 创建影子 chunk，逻辑分支继续延续
        shadow_chunk = self.copy_shadow_chunk()
        shadow_chunk.set_active_handle(name)
        return shadow_chunk

    @exposed_interface(type='connect_command')
    def connect_to(self, chunk: 'SchemaChunk') -> 'SchemaChunk':
        """
        连接到指定个 Chunk 节点，支持传入 create_chunk 创建好的实例、chunk dict、已定义好的 chunk 名称
        """
        if isinstance(chunk, str):
            chunks = self.workflow_schema.workflow.chunks
            chunk_info_list = chunk.split(".")
            if len(chunk_info_list) < 2:
                chunk_id = chunk_info_list[0]
                if chunk_id not in chunks:
                    raise Exception(
                        f"Can not find '{ chunk_id }' in workflow.chunks.")
                return self._raw_connect_to(chunks[chunk_id])
            else:
                chunk_id = chunk_info_list[0]
                handle_name = chunk_info_list[1]
                if chunk_id not in chunks:
                    raise Exception(
                        f"Can not find '{ chunk_id }' in workflow.chunks.")
                return self._raw_connect_to(chunks[chunk_id].handle(handle_name))
        elif callable(chunk):
            temp_chunk = self.workflow_schema.create_chunk(
                executor=chunk,
                type=EXECUTOR_TYPE_NORMAL,
                title=(
                    f"@{ chunk.__name__ }"
                    if not chunk.__name__ == "<lambda>"
                    else f"lambda-{ str(uuid.uuid4()) }"
                ),
            )
            return self._raw_connect_to(temp_chunk)
        else:
            return self._raw_connect_to(chunk)

    def set_active_handle(self, name: str = None):
        """设置激活的连接点，连接时会默认连接到该点上"""
        self.shared_ns['connection_ns']['active_handle'] = name

    def has_handle(self, name: str, from_inputs=True) -> bool:
        """判断连接手柄是否存在"""
        search_range = self.chunk.get('handles').get(
            'inputs' if from_inputs else 'outputs', [])
        return has_target_by_attr(search_range, 'handle', name)

    def copy_shadow_chunk(self, persist_supports_data=True):
        """获取到当前 chunk 的拷贝份（不干扰 chunk 自身运算逻辑），persist_supports_data 为是否保留支撑参数"""
        shadow_chunk = SchemaChunk(
            workflow_schema=self.workflow_schema,
            **self.get_raw_schema()
        )
        if persist_supports_data:
            shadow_chunk.shared_ns = deep_copy_simply(self.shared_ns)
            shadow_chunk.shared_chain_ns = deep_copy_simply(self.shared_chain_ns)

        return shadow_chunk
    
    def create_rel_chunk(self, persist_supports_data=True, **params) -> 'SchemaChunk':
        """在当前 schema 上创建一个新的 chunk """
        rel_chunk = self.workflow_schema.create_chunk(**params)
        if persist_supports_data:
            # 新挂载的 chunk，仅保留调用链，其它 api 运行数据保留
            rel_chunk.shared_chain_ns = deep_copy_simply(self.shared_chain_ns)
        return rel_chunk

    def get_raw_schema(self, use_origin=False):
        """获取原始的配置"""
        return self.chunk if use_origin else copy.deepcopy(self.chunk)
    
    def _raw_connect_to(self, chunk: 'SchemaChunk') -> 'SchemaChunk':
        """内部原生连接方法"""
        # 如果传入的是一个 dict 类型，自动进行实例化再连接
        target_chunk = self.workflow_schema.create_chunk(
            **chunk) if isinstance(chunk, dict) else chunk
        if type(target_chunk) != type(self):
            raise ValueError(
                f"The 'chunk' parameter to 'connect_to' is invalid.")

        # 检测 chunk 是否在当前 workflow 中有注册
        if not self.workflow_schema.get_chunk(target_chunk.chunk['id']):
            raise ValueError(
                f"The two chunk are not mounted under the same 'workflow'.")

        # 连接两 chunk
        self.workflow_schema.connect_chunk(
            self.chunk['id'],
            target_chunk.chunk['id'],
            self.shared_ns['connection_ns']['active_handle'] or DEFAULT_OUTPUT_HANDLE_VALUE,
            target_chunk.shared_ns['connection_ns']['active_handle'] or DEFAULT_INPUT_HANDLE_VALUE,
            self.chunk.get('connect_condition') or None,
            self.chunk.get('connect_condition_detail') or None,
        )
        target_chunk_shadow = target_chunk.copy_shadow_chunk(persist_supports_data=False)
        # 继承链路信息
        target_chunk_shadow.shared_chain_ns = deep_copy_simply(self.shared_chain_ns)
        return target_chunk_shadow

    def _fix_handles(self, custom_handles):
        """修正用户传入的 handles 配置格式"""
        # 处理默认 handle
        handles = custom_handles or {'inputs': [], 'outputs': []}
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
                        handle_list[idx] = {"handle": handle}

        fix_handle_core(handles['inputs'])
        fix_handle_core(handles['outputs'])
        return handles
