from ..lib.ChunkExecutorABC import ChunkExecutorABC
from ..lib.constants import EXECUTOR_TYPE_START

class StartExecutor(ChunkExecutorABC):
    def __init__(self, chunk_desc: dict, main_executor):
        self.type = EXECUTOR_TYPE_START
        self.chunk = chunk_desc

    def exec(self, inputs_with_handle_name: dict):
        return {
            "status": "success",
            "dataset": ''
        }
