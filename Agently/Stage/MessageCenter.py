import uuid
from .Stage import Stage

class MessageCenter:
    def __init__(self, private_max_workers=None, max_concurrent_tasks=None, on_error=None):
        self._stage = Stage(
            private_max_workers=private_max_workers,
            max_concurrent_tasks=max_concurrent_tasks,
            on_error=on_error,
            is_daemon=True
        )
        self._consumers = {}
    
    def register_consumer(self, handler):
        consumer_id = uuid.uuid4()
        self._consumers.update({ consumer_id: handler })
        return consumer_id
    
    def remove_consumer(self, consumer_id):
        del self._consumers[consumer_id]
    
    def put(self, data):
        for _, consumer_handler in self._consumers.items():
            self._stage.go(consumer_handler, data)
    
    def close(self):
        self._stage.close()