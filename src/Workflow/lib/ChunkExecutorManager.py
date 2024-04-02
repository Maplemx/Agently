class ChunkExecutorManager(object):
    def __init__(self):
        self.chunk_executors = {}

    def register(self, executor_id: str, executor_func: callable):
        self.chunk_executors.update({ executor_id: executor_func })
        return self

    def get(self, executor_id: str):
        if executor_id in self.chunk_executors:
            return self.chunk_executors[executor_id]
        else:
            return None