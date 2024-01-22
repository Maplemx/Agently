from ..lib.ChunkExecutorABC import ChunkExecutorABC
from ..lib.constants import EXECUTOR_TYPE_END

class UnknowExecutor(ChunkExecutorABC):
    def __init__(self, chunk_desc: dict, main_executor):
        self.type = EXECUTOR_TYPE_END
        self.chunk = chunk_desc
        self.main_executor = main_executor
        self.global_input_history = []

    def exec(self, inputs_with_handle_name: dict):
        chunk_data = self.chunk['data']
        return {
            "status": "error",
            "dataset": {},
            "error_msg": f"Unknow executor '{chunk_data.get('title', '-')}'({chunk_data.get('type', '')})"
        }
    
