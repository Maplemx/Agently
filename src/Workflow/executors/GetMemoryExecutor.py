from ..lib.ChunkExecutorABC import ChunkExecutorABC
from ..lib.constants import EXECUTOR_TYPE_NORMAL
from ..utils.runtime_supports import get_default_handle

class GetMemoryExecutor(ChunkExecutorABC):
    """
    用于从记忆里加载数据
    """

    def __init__(self, chunk_desc: dict, main_executor):
        self.type = EXECUTOR_TYPE_NORMAL
        self.chunk = chunk_desc
        self.main_executor = main_executor

    def exec(self, inputs_with_handle_name: dict):
        output_handle = get_default_handle(self.chunk.get('data').get('handles'), 'outputs')
        chunk_settings = self.chunk.get('data').get('settings') or {}
        memory_key = chunk_settings.get('name')
        if not output_handle or not memory_key:
            return {
                "status": "success",
                "dataset": {}
            }

        return {
            "status": "success",
            "dataset": {
                output_handle['handle']: self.main_executor.memory.get(memory_key)
            }
        }
    
