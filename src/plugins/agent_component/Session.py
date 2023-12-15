import uuid
import yaml
from .utils import ComponentABC

class Session(ComponentABC):
    def __init__(self, agent):
        self.agent = agent
        self.current_session_id = None
        self.full_chat_history = []
        self.recent_chat_history = []

    def toggle_auto_save(self, is_enabled: bool):
        self.agent.settings.set("plugin_settings.agent_component.Session.auto_save", is_enabled)
        return self.agent

    def set_max_length(self, max_length: int):
        self.agent.settings.set("plugin_settings.agent_component.Session.max_length", max_length)
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
        if self.agent.settings.get_trace_back("plugin_settings.agent_component.Session.auto_save"):
            self.agent.agent_storage.table("chat_history").set(self.current_session_id, self.full_chat_history).save()
        self.current_session_id = None
        self.full_chat_history = []
        self.recent_chat_history = []
        return self.agent

    def shorten_chat_history(self):
        if len(str(self.recent_chat_history)) > self.agent.settings.get_trace_back("plugin_settings.agent_component.Session.max_length"):
            self.recent_chat_history = self.recent_chat_history[1:]
            self.shorten_chat_history()
        else:
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
        if self.current_session_id != None:
            self.shorten_chat_history()
            return ("chat_history", self.recent_chat_history)

    def _suffix(self, event: str, data: any):
        if self.current_session_id != None:
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
                "set_chat_history_max_length": { "func": self.set_max_length },
            },
        }

def export():
    return ("Session", Session)