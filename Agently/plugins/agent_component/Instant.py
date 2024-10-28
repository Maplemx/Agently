import json5
from Agently.utils import Lexer
from .utils import ComponentABC
from Agently.utils import find_json

class Instant(ComponentABC):
    def __init__(self, agent: object):
        self.agent = agent
        self.__get_enable = self.agent.settings.get_trace_back("use_instant")
        self.__is_init = False
        self.__on_going_key_id = None
        self.__cached_value = {}
        self.__possible_keys = set()
        self.__emitted = set()
        self.__streaming_buffer = ""
        self.__instant_value = None
    
    def use_instant(self):
        self.agent.settings.set("use_instant", True)
        return self.agent
    
    def __scan_possible_keys(self, prompt_output_pointer, *, prefix:str=None):
        prefix = prefix if prefix != None else ""
        self.__possible_keys.add(prefix)
        if isinstance(prompt_output_pointer, dict):
            for key, value in prompt_output_pointer.items():
                self.__scan_possible_keys(value, prefix=prefix+f".{ key }")
        elif isinstance(prompt_output_pointer, list):
            for item in prompt_output_pointer:
                self.__scan_possible_keys(item, prefix=prefix+".[]")
        else:
            return
    
    async def __emit_instant(self, key, indexes, delta, value):
        event = "instant"
        data = {
            "key": key[1:],
            "indexes": indexes,
            "delta": delta,
            "value": value,
            "complete_value": self.__instant_value, 
        }
        self.agent.put_data_to_generator(event, data)
        await self.agent.call_event_listeners(event, data)

    async def __scan_instant_value(self, key: str, indexes:list, value:any):
        indexes = indexes[:]
        key_id = (key, json5.dumps(indexes))
        if key_id in self.__emitted or key not in self.__possible_keys:
            return
        if isinstance(value, dict):
            for item_key, item_value in value.items():
                await self.__scan_instant_value(key + f".{ item_key }", indexes, item_value)
            self.__cached_value[key_id] = value
        elif isinstance(value, list):
            for item_index, item_value in enumerate(value):
                temp = indexes[:]
                temp.append(item_index)
                await self.__scan_instant_value(key + f".[]", temp, item_value)
            self.__cached_value[key_id] = value
        else:
            if isinstance(value, str):
                cached_value = self.__cached_value[key_id] if key_id in self.__cached_value else ""
                cached_value = cached_value if cached_value != None else ""
                delta = value.replace(cached_value, "")
                if len(delta) > 0:
                    await self.__emit_instant(key + ".$delta", indexes, delta, value)
                    self.__cached_value[key_id] = value
                    self.__on_going_key_id = key_id
            else:
                self.__cached_value[key_id] = value
                self.__on_going_key_id = key_id
    def __judge_can_emit(self, current_key_id, on_going_key_id):
        if (not on_going_key_id[0].startswith(current_key_id[0])
            and on_going_key_id[0] + ".[]" != current_key_id[0]):
            return True
        current_indexes = json5.loads(current_key_id[1])
        on_going_indexes = json5.loads(on_going_key_id[1])
        for position, on_going_index in enumerate(on_going_indexes):
            if (len(current_indexes) >= position + 1
                and on_going_index > current_indexes[position]):
                return True
        return False
    
    async def __emit_waiting(self, *, is_done:bool=False):
        key_ids_to_del = []
        for key_id, value in self.__cached_value.items():
            indexes = json5.loads(key_id[1])
            if not is_done and key_id[0] == "":
                continue
            if key_id in self.__emitted:
                key_ids_to_del.append(key_id)
                continue
            if self.__on_going_key_id == None:
                continue
            if self.__judge_can_emit(key_id, self.__on_going_key_id) or is_done:
                if isinstance(value, dict):
                    await self.__emit_instant(key_id[0], indexes, value, value)
                    self.__emitted.add(key_id)
                    key_ids_to_del.append(key_id)
                elif isinstance(value, list):
                    await self.__emit_instant(key_id[0], indexes, value, value)
                    self.__emitted.add(key_id)
                    key_ids_to_del.append(key_id)
                else:
                    await self.__emit_instant(key_id[0], indexes, value, value)
                    self.__emitted.add(key_id)
                    key_ids_to_del.append(key_id)
        for key_id in key_ids_to_del:
            del self.__cached_value[key_id]

    async def _suffix(self, event: str, data: any):
        if (
            not self.agent.settings.get("use_instant")
            or "type" not in self.agent.request.response_cache
            or self.agent.request.response_cache["type"] != "JSON"
        ):
            return None
        if not self.__is_init:
            prompt_output = self.agent.request.response_cache["prompt"]["output"]
            if isinstance(prompt_output, dict):
                self.__scan_possible_keys(prompt_output)
            self.__is_init = True
        if event == "response:delta":
            self.__streaming_buffer += data
            instant_json_str = find_json(self.__streaming_buffer)
            if instant_json_str != None:
                lexer = Lexer()
                lexer.append_string(instant_json_str)
                try:
                    self.__instant_value = json5.loads(lexer.complete_json())
                    await self.__scan_instant_value("", [], self.__instant_value)
                    await self.__emit_waiting()
                except ValueError:
                    return None
                except Exception as e:
                    raise(e)
        if event == "response:done":
            self.__streaming_buffer += data
            instant_json_str = find_json(self.__streaming_buffer)
            if instant_json_str != None:
                lexer = Lexer()
                lexer.append_string(instant_json_str)
                try:
                    self.__instant_value = json5.loads(lexer.complete_json())
                    await self.__scan_instant_value("", [], self.__instant_value)
                    await self.__emit_waiting(is_done=True)
                except ValueError:
                    return None
                except Exception as e:
                    raise(e)

    def export(self):
        return {
            "suffix": self._suffix,
            "alias": {
                "use_instant": { "func": self.use_instant },
                "use_realtime": { "func": self.use_instant },
            },
        }

def export():
    return ("Instant", Instant)