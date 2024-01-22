import uuid
import copy
from .utils.verify import validate_dict
from .utils.find import has_target_by_attr
from .lib.constants import DEFAULT_INPUT_HANDLE, DEFAULT_OUTPUT_HANDLE

class SchemaChunk:
    """
    Workflow Schema 中的单个 chunk 结构，用于提供操作的 API
    """
    def __init__(self, chunk_desc: dict, workflow_schema):
        """
        必须参数 type, 可选参数 handles(连接点，{'inputs': [], 'outputs': []}) 字段，如没有 handles 字段，则会自动追加上默认设置、settings、title
        """
        # 校验必填字段
        verified_res = validate_dict(chunk_desc, ['type'])
        if verified_res['status'] == False:
            raise ValueError(f"Missing required key: '{verified_res['key']}'")

        self.chunk = {
            'id': chunk_desc.get('id', str(uuid.uuid4())),
            'title': chunk_desc.get('title'),
            'settings': chunk_desc.get('settings'),
            'type': chunk_desc.get('type'),
            'handles': chunk_desc.get('handles', {
                'inputs': [DEFAULT_INPUT_HANDLE.copy()],
                'outputs': [DEFAULT_OUTPUT_HANDLE.copy()]
            })
        }
        self.workflow_schema = workflow_schema
        # 当前激活的待连接的 handle 名
        self.active_handle = None
        # 解析出默认的连接 handle
        inputs = self.chunk.get('handles').get('inputs', [])
        self.default_input_handle = None
        if has_target_by_attr(inputs, 'handle', DEFAULT_INPUT_HANDLE['handle']):
            self.default_input_handle = DEFAULT_INPUT_HANDLE['handle']
        elif len(inputs) > 0:
            self.default_input_handle = inputs[0]['handle']

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
        shadow_chunk = SchemaChunk(self.get_raw_schema(), self.workflow_schema)
        shadow_chunk.set_active_handle(name)
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
        expect_source_handle = self.active_handle or self.default_output_handle
        if not self.has_handle(expect_source_handle, False):
            raise ValueError(f"The source chunk's connection handle '{expect_source_handle}' does not exist.")

        expect_target_handle = target_chunk.active_handle or target_chunk.default_input_handle
        if not target_chunk.has_handle(expect_target_handle):
            raise ValueError(f"The target chunk's connection handle '{expect_target_handle}' does not exist.")
        
        # 连接两 chunk
        self.workflow_schema.connect_chunk(
            self.chunk['id'],
            target_chunk.chunk['id'],
            expect_source_handle,
            expect_target_handle
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
        self.active_handle = name
    
    def has_handle(self, name: str, from_inputs = True) -> bool:
        """
        判断连接手柄是否存在
        """
        search_range = self.chunk.get('handles').get('inputs' if from_inputs else 'outputs', [])
        return has_target_by_attr(search_range, 'handle', name)