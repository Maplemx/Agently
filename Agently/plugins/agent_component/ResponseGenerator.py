from itertools import combinations
import threading
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
        thread.start()
        while True:
            try:
                item = self.data_queue.get()
                if item == (None, None):
                    break
                yield item
            except:
                continue
        self.data_queue = queue.Queue()
        thread.join()
    
    def get_instant_keys_generator(self, keys):
        if not isinstance(keys, list):
            if isinstance(keys, str):
                keys = keys.split("&")
            else:
                raise Exception("[Response Generator]", ".get_instant_keys_generator(<keys>) require a list or string input.\nKey format: <key string>?<indexes string split by ','>")
        key_indexes_list = []
        for key_str in keys:
            if isinstance(key_str, str):
                if "?" in key_str:
                    key, indexes_str = key_str.split("?")
                    index_list = indexes_str.split(",")
                    if index_list == [""]:
                        index_list = []
                else:
                    key = key_str
                    index_list = []
                indexes = []
                for index in index_list:
                    if index in ("_", "*"):
                        indexes.append(-1)
                    else:
                        indexes.append(int(index))
                key_indexes_list.append((key, indexes))
        self.agent.settings.set("use_instant", True)
        thread = threading.Thread(target=self.agent.start)
        thread.start()
        while True:
            try:
                item = self.data_queue.get()
                if item == (None, None):
                    break
                if item[0] == "instant":
                    indexes = item[1]["indexes"]
                    if (item[1]["key"], indexes) in key_indexes_list or (item[1]["key"], []) in key_indexes_list:
                        yield item[1]
                        continue
                    indexes_len = len(indexes)
                    for r in range(1, indexes_len + 1):
                        for indices in combinations(range(indexes_len), r):
                            possible_indexes = indexes[:]
                            for i in indices:
                                possible_indexes[i] = -1
                            if (item[1]["key"], possible_indexes) in key_indexes_list:
                                yield item[1]
                                break
            except:
                continue
        self.data_queue = queue.Queue()
        thread.join()

    def get_instant_generator(self):
        self.agent.settings.set("use_instant", True)
        thread = threading.Thread(target=self.agent.start)
        thread.start()
        while True:
            try:
                item = self.data_queue.get()
                if item == (None, None):
                    break
                if item[0] == "instant":
                    yield item[1]
            except Exception as e:
                continue
        self.data_queue = queue.Queue()
        thread.join()
    
    def get_generator(self):
        thread = threading.Thread(target=self.agent.start)
        thread.start()
        while True:
            try:
                item = self.data_queue.get()
                if item == (None, None):
                    break
                if not item[0].endswith(("_origin")):
                    yield item
            except:
                continue
        self.data_queue = queue.Queue()
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
                "get_instant_generator": { "func": self.get_instant_generator, "return_value": True },
                "get_realtime_generator": { "func": self.get_instant_generator, "return_value": True },
                "get_instant_keys_generator": { "func": self.get_instant_keys_generator, "return_value": True },
                "get_complete_generator": { "func": self.get_complete_generator, "return_value": True },
            },
        }

def export():
    return ("ResponseGenerator", ResponseGenerator)