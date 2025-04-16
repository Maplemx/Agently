from itertools import combinations
from .utils import ComponentABC
from Agently.Stage import Stage, Tunnel
from contextlib import contextmanager

class ResponseGenerator(ComponentABC):
    def __init__(self, agent):
        super().__init__(agent)
        self._tunnel = Tunnel()

    @contextmanager
    def _create_start_stage(self):
        try:
            stage = Stage(is_daemon=True)
            yield stage.func(self.agent.start)
        finally:
            stage.close()

    def put_data_to_generator(self, event, data):
        if (event, data) != (None, None):
            self._tunnel.put((event, data))
        else:
            self._tunnel.put_stop()

    def get_complete_generator(self):
        with self._create_start_stage() as stage:
            stage.go()
            for item in self._tunnel.get():
                yield item
            self._tunnel = Tunnel()
    
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
        with self._create_start_stage() as stage:
            stage.go()
            for item in self._tunnel.get():
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
            self._tunnel = Tunnel()
    
    def get_instant_generator(self):
        self.agent.settings.set("use_instant", True)
        try:
            with self._create_start_stage() as stage:
                stage.go()
                for item in self._tunnel.get():
                    if item[0] == "instant":
                        yield item[1]
        finally:
            self._tunnel = Tunnel()
    
    def get_generator(self):
        try:
            with self._create_start_stage() as stage:
                stage.go()
                for item in self._tunnel.get():
                    if not item[0].endswith(("_origin")):
                        yield item
        finally:
            self._tunnel = Tunnel()
    
    def get_delta_generator(self):
        with self._create_start_stage() as stage:
            stage.go()
            for event, data in self._tunnel.get():
                if event == "response:delta":
                    yield data
            self._tunnel = Tunnel()
        
    async def _suffix(self, event, data):
        if event != "response:finally":
            self._tunnel.put((event, data))
        else:
            self._tunnel.put_stop()
    
    def export(self):
        return {
            "suffix": self._suffix,
            "alias": { 
                "put_data_to_generator": { "func": self.put_data_to_generator },
                "get_generator": { "func": self.get_generator, "return_value": True },
                "get_delta_generator": { "func": self.get_delta_generator, "return_value": True },
                "get_instant_generator": { "func": self.get_instant_generator, "return_value": True },
                "get_realtime_generator": { "func": self.get_instant_generator, "return_value": True },
                "get_instant_keys_generator": { "func": self.get_instant_keys_generator, "return_value": True },
                "get_complete_generator": { "func": self.get_complete_generator, "return_value": True },
            },
        }

def export():
    return ("ResponseGenerator", ResponseGenerator)