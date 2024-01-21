from ..lib.ChunkExecutorABC import ChunkExecutorABC
from ..lib.constants import EXECUTOR_TYPE_NORMAL

class SaveMemoryExecutor(ChunkExecutorABC):
    """
    用于将数据存入记忆
    """

    def __init__(self, chunk_desc: dict, main_executor):
        self.type = EXECUTOR_TYPE_NORMAL
        self.chunk = chunk_desc
        self.main_executor = main_executor

    def exec(self, inputs_with_handle_name: dict):
        if inputs_with_handle_name and len(inputs_with_handle_name):
            self.main_executor.memory.save(inputs_with_handle_name)

        return {
            "status": "success",
            "dataset": {}
        }
    
