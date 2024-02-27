from .MainExecutor import MainExecutor
from .utils.exec_tree import generate_exec_tree
from .Schema import Schema
from ..utils import RuntimeCtx
from .._global import global_settings
from .executors.install import mount_built_in_executors
from .lib.constants import EXECUTOR_TYPE_NORMAL

class Workflow:
    def __init__(self, *, schema_data: dict = None, settings: dict = {}):
        """
        Workflow，初始参数 schema_data 形如 { 'chunks': [], 'edges': [] }，handler 为要处理响应的函数
        """
        # 处理设置
        self.settings = RuntimeCtx(parent = global_settings)
        if settings:
            self.settings.update_by_dict(settings)
        # 初始 schema
        self.schema = Schema(schema_data or {'chunks': [], 'edges': []})
        # 初始化执行器
        self.executor = MainExecutor(settings)
        # 装载内置类型
        mount_built_in_executors(self.executor)
        # Chunk Storage
        self.chunks = {}

    def chunk(self, chunk_id: str, type=EXECUTOR_TYPE_NORMAL, **chunk_desc):
        def create_chunk_decorator(func: callable):
            return self.chunks.update({
                chunk_id: self.schema.create_chunk(
                        executor = func,
                        type = type,
                        **chunk_desc
                    )
            })
        return create_chunk_decorator
    
    def startup(self):
        exec_logic_tree = generate_exec_tree(self.schema)
        self.executor.startup(exec_logic_tree)
    
    def reset(self, schema_data: dict):
        self.schema = Schema(schema_data or {'chunks': [], 'edges': []})