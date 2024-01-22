from ..lib.ChunkExecutorABC import ChunkExecutorABC
from ..lib.constants import EXECUTOR_TYPE_END

class PrintExecutor(ChunkExecutorABC):
    def __init__(self, chunk_desc: dict, main_executor):
        self.type = EXECUTOR_TYPE_END
        self.chunk = chunk_desc

    def exec(self, inputs_with_handle_name: dict):
        res = {}
        if len(inputs_with_handle_name) > 0:
            # 从各句柄读取数据，作为最终结果返回
            res = inputs_with_handle_name
        
        print(res)

        return {
            "status": "success",
            "dataset": res
        }
    
