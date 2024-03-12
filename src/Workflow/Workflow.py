from .MainExecutor import MainExecutor
from .utils.exec_tree import resolve_runtime_data
from .Schema import Schema
from ..utils import RuntimeCtx
from .._global import global_settings
from .executors.install import mount_built_in_executors
from .lib.constants import EXECUTOR_TYPE_NORMAL, DEFAULT_INPUT_HANDLE_VALUE, DEFAULT_OUTPUT_HANDLE_VALUE
from .lib.painter import draw_with_mermaid
from Agently.utils import IdGenerator

class Workflow:
    def __init__(self, *, schema_data: dict = None, settings: dict = {}, workflow_id:str=None):
        """
        Workflow，初始参数 schema_data 形如 { 'chunks': [], 'edges': [] }，handler 为要处理响应的函数
        """
        self.workflow_id = workflow_id or IdGenerator("workflow").create()
        # 处理设置
        self.settings = RuntimeCtx(parent = global_settings)
        if settings:
            self.settings.update_by_dict(settings)
        # 初始 schema
        self.schema = Schema(schema_data or {'chunks': [], 'edges': []})
        # 初始化执行器
        self.executor = MainExecutor(self.workflow_id, self.settings)
        # 装载内置类型
        mount_built_in_executors(self.executor)
        # Chunk Storage
        self.chunks = {}

    def chunk(self, chunk_id: str, type=EXECUTOR_TYPE_NORMAL, **chunk_desc):
        if "title" not in chunk_desc or chunk_desc["title"] == "":
            chunk_desc.update({ "title": chunk_id })
        def create_chunk_decorator(func: callable):
            return self.chunks.update({
                chunk_id: self.schema.create_chunk(
                        executor = func,
                        type = type,
                        **chunk_desc
                    )
            })
        return create_chunk_decorator
    
    def start(self):
        runtime_data = resolve_runtime_data(self.schema)
        self.executor.start(runtime_data)
    
    def reset(self, schema_data: dict):
        self.schema = Schema(schema_data or {'chunks': [], 'edges': []})
    
    def draw(self, type='mermaid'):
        """绘制出图形，默认使用 mermaid，可点击 https://mermaid-js.github.io/mermaid-live-editor/edit 粘贴查看效果"""
        return draw_with_mermaid(self.schema)
