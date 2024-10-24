import threading
import asyncio
import queue
from .utils import ComponentABC

class ResponseGenerator(ComponentABC):
    def __init__(self, agent):
        self.agent = agent
        self.data_queue = queue.Queue()
    
    def put_data_to_generator(self, event, data):
        self.data_queue.put((event, data))

    def get_complete_generator(self):
        thread = threading.Thread(target=self.agent.start)
        thread.daemon = True
        thread.start()
        while True:
            try:
                item = self.data_queue.get_nowait()
                if item == (None, None):
                    break
                yield item
            except:
                continue
        thread.join()
    
    def get_realtime_generator(self):
        self.agent.settings.set("use_realtime", True)
        thread = threading.Thread(target=self.agent.start)
        thread.daemon = True
        thread.start()
        while True:
            try:
                item = self.data_queue.get_nowait()
                if item == (None, None):
                    break
                if item[0] == "realtime":
                    yield item[1]
            except:
                continue
        thread.join()
    
    def get_generator(self):
        thread = threading.Thread(target=self.agent.start)
        thread.daemon = True
        thread.start()
        while True:
            try:
                item = self.data_queue.get_nowait()
                if item == (None, None):
                    break
                if not item[0].endswith(("_origin")):
                    yield item
            except:
                continue
        thread.join()

    def _suffix(self, event, data):
        if event != "response:finally":
            self.put_data_to_generator(event, data)
        else:
            self.put_data_to_generator(None, None)
    
    def export(self):
        return {
            "suffix": self._suffix,
            "alias": { 
                "put_data_to_generator": { "func": self.put_data_to_generator },
                "get_generator": { "func": self.get_generator, "return_value": True },
                "get_realtime_generator": { "func": self.get_realtime_generator, "return_value": True },
                "get_complete_generator": { "func": self.get_complete_generator, "return_value": True },
            },
        }

def export():
    return ("ResponseGenerator", ResponseGenerator)