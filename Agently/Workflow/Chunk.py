import uuid
import copy
from .utils.find import has_target_by_attr
from .lib.constants import DEFAULT_INPUT_HANDLE, DEFAULT_OUTPUT_HANDLE, EXECUTOR_TYPE_NORMAL

SPECIAL_CHUNK_TYPES = ['Start']
class SchemaChunk:
    """
    Workflow Schema 中的单个 chunk 结构，用于辅助提供操作的 API，实际运行时，提供 chunk 描述参数交给 MainExecutor 执行
    """

    def __init__(self, workflow_schema = None, type = EXECUTOR_TYPE_NORMAL, executor: callable = None, **chunk_desc):
        """
        可选参数 handles(连接点，{'inputs': [], 'outputs': []}) 字段，如没有 handles 字段，则会自动追加上默认设置、interactions、title，必选参数 executor，或 type 为 'Start'
        """
        # 校验必填字段(要么 type 为特殊类型，否则必须包含 executor)
        if not type or (type not in SPECIAL_CHUNK_TYPES):
            if not executor:
                raise ValueError("Missing required key: 'executor'")

        self.chunk = {
            'id': chunk_desc.get('id', str(uuid.uuid4())),
            'title': chunk_desc.get('title'),
            'interactions': chunk_desc.get('interactions') or {}, # 交互配置
            'type': type or EXECUTOR_TYPE_NORMAL,
            'executor': executor,
            'handles': self._fix_handles(chunk_desc.get('handles')),
            # 连接条件（默认无条件连通）
            'connect_condition': chunk_desc.get('connect_condition') or None,
            # 当前激活的待连接的 handle 名
            'active_handle': chunk_desc.get('active_handle') or None
        }

        self.workflow_schema = workflow_schema

        # 解析出默认的输入连接点(有 input 直接用 input 做默认，否则取第一个手柄为默认连接点)
        inputs = self.chunk.get('handles').get('inputs', [])
        self.default_input_handle = None
        if has_target_by_attr(inputs, 'handle', DEFAULT_INPUT_HANDLE['handle']):
            self.default_input_handle = DEFAULT_INPUT_HANDLE['handle']
        elif len(inputs) > 0:
            self.default_input_handle = inputs[0]['handle']

        # 解析出默认的输出连接点(有 output 直接用 output 做默认，否则取第一个手柄为默认连接点)
        outputs = self.chunk.get('handles').get('outputs', [])
        self.default_output_handle = None
        if has_target_by_attr(outputs, 'handle', DEFAULT_OUTPUT_HANDLE['handle']):
            self.default_output_handle = DEFAULT_OUTPUT_HANDLE['handle']
        elif len(outputs) > 0:
            self.default_output_handle = outputs[0]['handle']
    
    def handle(self, name: str):
        """
        Chunk 的连接点
        """
        if not self.has_handle(name) and not self.has_handle(name, False):
            raise ValueError(f"The handle '{name}' for chunk '{self.chunk.get('title', self.chunk['id'])}' does not exist.")
        shadow_chunk = SchemaChunk(
            workflow_schema=self.workflow_schema,
            **self.get_raw_schema()
        )
        shadow_chunk.set_active_handle(name)
        return shadow_chunk
    
    def if_condition(self, condition: callable = None):
        """
        按条件连接
        """
        shadow_chunk = SchemaChunk(
            workflow_schema=self.workflow_schema,
            **self.get_raw_schema()
        )
        shadow_chunk.set_connect_condition(condition)
        return shadow_chunk

    def else_condition(self):
        """
        按当前条件的反条件连接
        """
        current_condition = self.chunk.get('connect_condition')
        if not current_condition:
            current_condition = lambda values: True
        else_condition_func = lambda values: not current_condition(values)
        shadow_chunk = SchemaChunk(
            workflow_schema=self.workflow_schema,
            **self.get_raw_schema()
        )

        shadow_chunk.set_connect_condition(else_condition_func)
        return shadow_chunk

    def connect_to(self, chunk):
        """
        连接到指定个 Chunk 节点，支持传入 create_chunk 创建好的实例，也支持传入 chunk dict
        """
        # 如果传入的是一个 dict 类型，自动进行实例化再连接
        target_chunk = self.workflow_schema.create_chunk(chunk) if isinstance(chunk, dict) else chunk
        if not isinstance(target_chunk, SchemaChunk):
            raise ValueError(f"The 'chunk' parameter to 'connect_to' is invalid.")

        # 检测 chunk 是否在当前 workflow 中有注册
        if not self.workflow_schema.get_chunk(target_chunk.chunk['id']):
            raise ValueError(f"The two chunk are not mounted under the same 'workflow'.")

        # 解析出连接手柄，并判断合法性
        expect_source_handle = self.chunk.get('active_handle') or self.default_output_handle
        if not self.has_handle(expect_source_handle, False):
            raise ValueError(f"The source chunk's connection handle '{expect_source_handle}' does not exist.")

        expect_target_handle = target_chunk.chunk.get('active_handle') or target_chunk.default_input_handle
        if not target_chunk.has_handle(expect_target_handle):
            raise ValueError(f"The target chunk's connection handle '{expect_target_handle}' does not exist.")
        
        # 连接两 chunk
        self.workflow_schema.connect_chunk(
            self.chunk['id'],
            target_chunk.chunk['id'],
            expect_source_handle,
            expect_target_handle,
            self.chunk.get('connect_condition') or None
        )
        return self
    
    def get_raw_schema(self):
        return copy.deepcopy(self.chunk)
    
    def set_active_handle(self, name: str = None):
        """
        设置激活的连接点，连接时会默认连接到该点上
        """
        if name is not None:
            if not self.has_handle(name) and not self.has_handle(name, False):
                raise ValueError(
                    f"The handle '{name}' for chunk '{self.chunk.get('title', self.chunk['id'])}' does not exist.")
        self.chunk['active_handle'] = name
    
    def set_connect_condition(self, condition: callable = None):
        """
        设置连接的条件
        """
        self.chunk['connect_condition'] = condition
    
    def has_handle(self, name: str, from_inputs = True) -> bool:
        """
        判断连接手柄是否存在
        """
        search_range = self.chunk.get('handles').get('inputs' if from_inputs else 'outputs', [])
        return has_target_by_attr(search_range, 'handle', name)

    def _fix_handles(self, custom_handles):
        """修正用户传入的 handles 配置"""
        # 处理默认 handle
        handles = custom_handles or {
            'inputs': [DEFAULT_INPUT_HANDLE.copy()],
            'outputs': [DEFAULT_OUTPUT_HANDLE.copy()]
        }
        if 'inputs' not in handles:
            handles['inputs'] = [DEFAULT_INPUT_HANDLE.copy()]
        if 'outputs' not in handles:
            handles['outputs'] = [DEFAULT_OUTPUT_HANDLE.copy()]

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