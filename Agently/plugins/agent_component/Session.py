import uuid
import yaml
from .utils import ComponentABC
from Agently.utils import RuntimeCtxNamespace

class Session(ComponentABC):
    def __init__(self, agent):
        self.agent = agent
        self.settings = RuntimeCtxNamespace("plugin_settings.agent_component.Session", self.agent.settings)
        self.current_session_id = None
        self.full_chat_history = []
        self.recent_chat_history = []
        self.abstract = RuntimeCtxNamespace("abstract", self.agent.agent_runtime_ctx)

    def toggle_auto_save(self, is_enabled: bool):
        self.settings.set("auto_save", is_enabled)
        return self.agent

    def toggle_strict_orders(self, is_strict_orders: bool):
        self.settings.set("strict_orders", is_strict_orders)
        return self.agent

    def toggle_manual_chat_history(self, is_manual_chat_history: bool):
        self.settings.set("manual_chat_history", is_manual_chat_history)
        return self.agent

    def set_max_length(self, max_length: int):
        self.settings.set("max_length", max_length)
        return self.agent

    
    def active(self, session_id: str=None):
        if self.current_session_id != None:
            self.stop()
        if session_id == None:
            self.current_session_id = str(uuid.uuid1())
        else:
            self.current_session_id = session_id
            full_chat_history = self.agent.agent_storage.table("chat_history").get(session_id)
            full_chat_history = full_chat_history if full_chat_history else []
            self.full_chat_history.extend(full_chat_history)
            self.recent_chat_history.extend(full_chat_history)
        return self.current_session_id

    def save(self):
        self.agent.agent_storage.table("chat_history").set(self.current_session_id, self.full_chat_history).save()
        return self.agent

    def stop(self):
        if self.settings.get_trace_back("auto_save", True):
            self.agent.agent_storage.table("chat_history").set(self.current_session_id, self.full_chat_history).save()
        self.current_session_id = None
        self.full_chat_history = []
        self.recent_chat_history = []
        return self.agent

    def __get_shorten_chat_history(self, current_chat_history: list, max_length: int):
        if len(str(current_chat_history)) > max_length:
            self.__get_shorten_chat_history(current_chat_history[1:], max_length)
        else:
            return current_chat_history

    def shorten_chat_history(self):
        self.recent_chat_history = self.__get_shorten_chat_history(self.recent_chat_history, self.settings.get_trace_back("max_length"))
        return self.agent

    def add_chat_history(self, role: str, content: str):
        if role not in ("user", "assistant"):
            raise Exception("[Agent Component]: Session - add_chat_history() only accept role type 'user' or 'assistant'.")
        is_strict_orders = self.settings.get_trace_back("strict_orders")
        if is_strict_orders:
            if len(self.full_chat_history) > 0:
                if self.full_chat_history[-1]["role"] == role:
                    self.full_chat_history[-1]["content"] += "\n" + content
                    self.recent_chat_history[-1]["content"] += "\n" + content
                else:
                    self.full_chat_history.append({ "role": role, "content": content})
                    self.recent_chat_history.append({ "role": role, "content": content})
            else:
                if role == "user":
                    self.full_chat_history.append({ "role": role, "content": content})
                    self.recent_chat_history.append({ "role": role, "content": content})
                else:
                    self.full_chat_history.extend([
                        { "role": "user", "content": "[EMPTY]" },
                        { "role": role, "content": content},
                    ])
                    self.recent_chat_history.extend([
                        { "role": "user", "content": "[EMPTY]" },
                        { "role": role, "content": content},
                    ])
        else:
            self.full_chat_history.append({ "role": role, "content": content})
            self.recent_chat_history.append({ "role": role, "content": content})
        return self.agent

    def get_chat_history(self, *, is_shorten: bool=False):
        if is_shorten:
            self.recent_chat_history = self.__get_shorten_chat_history(self.recent_chat_history, self.settings.get_trace_back("max_length", 12000))
            return self.recent_chat_history
        else:
            return self.full_chat_history

    def rewrite_chat_history(self, new_chat_history: list):
        self.full_chat_history = new_chat_history.copy()
        self.recent_chat_history = new_chat_history.copy()
        return self.agent

    def __find_input(self, input_data: any):
        if isinstance(input_data, str):
            return input_data
        elif isinstance(input_data, dict):
            if "input" in input_data:
                return str(input_data["input"])
            elif "question" in input_data:
                return str(input_data["question"])
            elif "target" in input_data:
                return str(input_data["target"])
            elif "goal" in input_data:
                return str(input_data["goal"])
            else:
                return yaml.dump(input_data, allow_unicode=True, sort_keys=False)
        else:
            return str(input_data)

    def __find_reply(self, reply_data: any):
        if isinstance(reply_data, str):
            return reply_data
        elif isinstance(reply_data, dict):
            if "reply" in reply_data:
                return str(reply_data["reply"])
            elif "result" in reply_data:
                return str(reply_data["result"])
            elif "response" in reply_data:
                return str(reply_data["response"])
            elif "anwser" in reply_data:
                return str(reply_data["anwser"])
            elif "output" in reply_data:
                return str(reply_data["output"])
            else:
                return yaml.dump(reply_data, allow_unicode=True, sort_keys=False)
        else:
            return str(reply_data)

    def _prefix(self):
        prefix_result = {}
        if self.current_session_id != None:
            self.shorten_chat_history()
            prefix_result.update({ "chat_history": self.recent_chat_history })
        abstract = self.abstract.get()
        if abstract:
            prefix_result.update({ "abstract": abstract })
        return prefix_result

    def _suffix(self, event: str, data: any):
        is_manual_chat_history = self.settings.get_trace_back("manual_chat_history", False)
        if self.current_session_id != None and not is_manual_chat_history:
            if event == "response:finally":
                new_chat_history = [
                    { "role": "user", "content": self.__find_input(data["prompt"]["input"]) },
                    { "role": "assistant", "content": self.__find_reply(data["reply"]) }
                ]
                self.full_chat_history.extend(new_chat_history)
                self.recent_chat_history.extend(new_chat_history)

    def export(self):
        return {
            "prefix": self._prefix,
            "suffix": self._suffix,
            "alias": {
                "active_session": { "func": self.active, "return_value": True },
                "save_session": { "func": self.save },
                "stop_session": { "func": self.stop },
                "toggle_session_auto_save": { "func": self.toggle_auto_save },
                "toggle_strict_orders": { "func": self.toggle_strict_orders },
                "toggle_manual_chat_history": { "func": self.toggle_manual_chat_history },
                "set_chat_history_max_length": { "func": self.set_max_length },
                "add_chat_history": { "func": self.add_chat_history },
                "get_chat_history": { "func": self.get_chat_history, "return_value": True },
                "rewrite_chat_history": { "func": self.rewrite_chat_history },
                "set_abstract": { "func": self.abstract.assign },
            },
        }

def export():
    return ("Session", Session)