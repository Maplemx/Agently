import asyncio
import logging
from .MainExecutor import MainExecutor
from .Schema import Schema
from .executors.install import mount_built_in_executors
from .lib.ChunkExecutorManager import ChunkExecutorManager
from .lib.constants import EXECUTOR_TYPE_NORMAL
from .lib.painter import draw_with_mermaid
from .yamlflow.yamlflow import start_yaml_from_str, start_yaml_from_path
from .utils.exec_tree import generate_executed_schema
from .utils.logger import get_default_logger
from .utils.runner import run_async
from ..utils import RuntimeCtx
from .._global import global_settings
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
        # logger
        workflow_default_logger = get_default_logger(self.workflow_id, level=logging.DEBUG if self.settings.get_trace_back("is_debug") else logging.WARN)
        self.logger = self.settings.get('logger', workflow_default_logger)
        # 初始 schema
        self.schema = Schema(
            schema_data=schema_data or {'chunks': [], 'edges': []},
            workflow=self,
            logger=self.logger
        )
        # 初始化执行器
        self.executor = MainExecutor(
            workflow_id=self.workflow_id,
            settings=self.settings,
            logger=self.logger
        )
        # Get Storage From Executor
        self.storage = self.executor.store
        # 装载内置类型
        mount_built_in_executors(self.executor)
        # Chunk Storage
        self.chunks = {}
        # Executor Manager
        self.executor_manager = ChunkExecutorManager()
        # Short Cut
        self.chunk("start", type = "Start")(lambda:None)
        self.chunk("end", type = "End")(lambda:None)
        self.connect_to = self.chunks["start"].connect_to

    def chunk(self, chunk_id: str=None, type=EXECUTOR_TYPE_NORMAL, **chunk_desc):
        is_class = chunk_desc.get("is_class", False)
        if not is_class:
            def create_chunk_decorator(func: callable):
                nonlocal chunk_id, type, chunk_desc
                if not chunk_id or not isinstance(chunk_id, str):
                    chunk_id = func.__name__
                if "title" not in chunk_desc or chunk_desc["title"] == "":
                    chunk_desc.update({ "title": chunk_id })
                return self.chunks.update({
                    chunk_id: self.schema.create_chunk(
                            executor = func,
                            type = type,
                            **chunk_desc
                        )
                })
            return create_chunk_decorator
        else:
            return self.chunk_class(chunk_id, type, **chunk_desc)

    def chunk_class(self, chunk_id: str=None, type=EXECUTOR_TYPE_NORMAL, **chunk_desc):
        def create_chunk_decorator(func: callable):
            nonlocal chunk_id, type, chunk_desc
            if not chunk_id or not isinstance(chunk_id, str):
                chunk_id = f"@{ func.__name__ }"
            if "title" not in chunk_desc or chunk_desc["title"] == "":
                chunk_desc.update({ "title": chunk_id })
            return self.chunks.update({
                chunk_id: {
                    "executor": func,
                    "type": type,
                    **chunk_desc
                }
            })
        return create_chunk_decorator

    def register_executor_func(self, executor_id: str, executor_func: callable):
        self.executor_manager.register(executor_id, executor_func)
        return self

    def executor_func(self, executor_id: str):
        def register_executor_decorator(func: callable):
            return self.executor_manager.register(executor_id, func)
        return register_executor_decorator

    def start_yaml(self, yaml_str=None, *, path=None, draw=False):
        if yaml_str:
            return start_yaml_from_str(self, yaml_str, draw=draw)
        elif path:
            return start_yaml_from_path(self, path, draw=draw)
        else:
            raise Exception("[Workflow] At least one parameter in `yaml_str` and `path` is required when using workflow.load_yaml().")

    async def start_async(self, start_data=None, *, storage=None):
        executed_schema = generate_executed_schema(self.schema.compile())
        res = await self.executor.start(executed_schema, start_data, storage=storage)
        return res

    def start(self, start_data = None, *, storage=None):
        return run_async(self.start_async(start_data, storage=storage))

    def reset_runtime_status(self):
        """重置运行数据"""
        self.executor.reset_all_runtime_status()
        return self

    def reset(self, schema_data: dict = None):
        """彻底重置（包含注册的chunk和连接关系）"""
        self.executor.reset_all_runtime_status()
        self.schema = Schema(schema_data or {'chunks': [], 'edges': []})
        return self
    
    def reset_connection(self):
        """重置链接关系(保留 chunk 注册)"""
        self.executor.reset_all_runtime_status()
        self.schema.remove_all_connection()
        return self
    
    def get_runtime_store(self):
        return self.executor.store

    def draw(self, type='mermaid'):
        """绘制出图形，默认使用 mermaid，可点击 https://mermaid-js.github.io/mermaid-live-editor/edit 粘贴查看效果"""
        return draw_with_mermaid(self.schema.compile())
