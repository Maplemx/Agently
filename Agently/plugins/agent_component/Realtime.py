import json5
from Agently.utils import Lexer
from .utils import ComponentABC
from Agently.utils import find_json, DataGenerator

class Realtime(ComponentABC):
    def __init__(self, agent: object):
        self.agent = agent
        self._is_enable = False
        self._is_init = False
        self._output_data_frame = None
        self._target_keys = []
        self._buffer = ""
        self._data_generator = DataGenerator()
        self._streamed_keys = []
        self._ongoing_key = None
        self._ongoing_value = None
        self._last_value = None
    
    def use_realtime(self):
        self._is_enable = True
        return self.agent
    
    def __get_output_data_frame(self, prompt_output:dict, prefix:str=""):
        result = {}
        for key, value in prompt_output.items():
            if isinstance(key, dict):
                prefix += f"{key}."
                result.update({ key: self.__get_output_data_frame(value, prefix) })
            else:
                self._target_keys.append(prefix + key)
                result.update({ key: None })
        return result
    
    async def __scan_realtime_value(self, realtime_value:dict, prefix:str="", output_data_frame_pointer:dict={}):
        for key, value in realtime_value.items():
            if isinstance(value, dict):
                if key in output_data_frame_pointer:
                    await self.__scan_realtime_value(value, prefix + f"{key}.", output_data_frame_pointer[key])
            else:
                if self._ongoing_key == (prefix + key):
                    self._ongoing_value = value
                    if self._last_value and isinstance(self._ongoing_value, str):
                        delta = self._ongoing_value.replace(self._last_value, "")
                    else:
                        delta = value
                    if delta != "":
                        await self.agent.call_event_listeners(
                            "response:realtime",
                            {
                                "key": self._ongoing_key,
                                "value": self._ongoing_value,
                                "delta": delta,
                                "complete_value": realtime_value,
                            },
                        )
                        self._last_value = value
                if self._ongoing_key != prefix + key:
                    if (prefix + key) not in self._streamed_keys and value not in (None, ""):
                        if self._ongoing_key != None:
                            await self.agent.call_event_listeners(f"key_stop:{ self._ongoing_key }", None)
                        self._ongoing_key = prefix + key
                        await self.agent.call_event_listeners(f"key_start:{ self._ongoing_key }", None)
                        self._streamed_keys.append(prefix + key)
                        self._ongoing_value = value
                        if self._last_value and isinstance(self._ongoing_value, str):
                            delta = self._ongoing_value.replace(self._last_value, "")
                        else:
                            delta = value
                        if delta != "":
                            await self.agent.call_event_listeners(
                                "response:realtime",
                                {
                                    "key": self._ongoing_key,
                                    "value": self._ongoing_value,
                                    "delta": delta,
                                    "complete_value": realtime_value,
                                },
                            )
                            self._last_value = value
                    if (prefix + key) in self._streamed_keys or value in (None, ""):
                        continue
    
    async def _suffix(self, event:str, data:any):
        if not self._is_enable or "type" not in self.agent.request.response_cache or self.agent.request.response_cache["type"] != "JSON":
            return None
        else:
            if not self._is_init:
                prompt_output = self.agent.request.response_cache["prompt"]["output"]
                if isinstance(prompt_output, dict):
                    self._output_data_frame = self.__get_output_data_frame(prompt_output)
                self._is_init = True
            if event == "response:delta":
                self._buffer += data
                realtime_json_str = find_json(self._buffer)
                if realtime_json_str != None:
                    lexer = Lexer()
                    lexer.append_string(realtime_json_str)
                    realtime_value = json5.loads(lexer.complete_json())
                    if self._output_data_frame == None:
                        if self._last_value and isinstance(realtime_value, str):
                            delta = realtime_value.replace(self._last_value, "")
                        else:
                            delta = realtime_value
                        if delta != "":
                            await self.agent.call_event_listeners(
                                "response:realtime",
                                {
                                    "key": None,
                                    "value": realtime_value,
                                    "delta": delta,
                                    "complete_value": realtime_value,
                                },
                            )
                            self._last_value = realtime_value
                    else:
                        if isinstance(realtime_value, dict):
                            await self.__scan_realtime_value(realtime_value, "", self._output_data_frame)
    
    def export(self):
        return {
            "prefix": None,
            "suffix": self._suffix,
            "alias": {
                "use_realtime": { "func": self.use_realtime }
            },
        }

def export():
    return ("Realtime", Realtime)