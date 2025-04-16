import asyncio
from itertools import combinations
from .utils import ComponentABC
from Agently.utils import RuntimeCtx, RuntimeCtxNamespace

class EventListener(ComponentABC):
    def __init__(self, agent: object):
        self.agent = agent
        self.agent_listeners = RuntimeCtxNamespace("event_listeners", self.agent.agent_runtime_ctx)
        self.listeners = RuntimeCtxNamespace("event_listeners", RuntimeCtx(parent=self.agent.agent_runtime_ctx))
        self.listeners.set({})
        self.async_tasks = []

    def add(self, event:str, listener: callable, *, is_await:bool=False, is_agent_event:bool=False):
        event = event.replace(".", "->")
        if event == "realtime":
            self.agent.settings.set("use_instant", True)
            event = "instant"
        if event.startswith("realtime:"):
            self.agent.settings.set("use_instant", True)
            event = "instant:" + event[9:]
        if event == "instant" or event.startswith("instant:"):
             self.agent.settings.set("use_instant", True)
        if event.startswith("instant:"):
            event_data = event.replace(" ", "").split(":")
            keys = event_data[1].replace("->", ".").split("&")
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
            async def instant_hook_handler(data):
                indexes = data["indexes"]
                if (data["key"], indexes) in key_indexes_list or (data["key"], []) in key_indexes_list:
                    if asyncio.iscoroutinefunction(listener):
                        await listener(data)
                    else:
                        listener(data)
                indexes_len = len(indexes)
                for r in range(1, indexes_len + 1):
                    for indices in combinations(range(indexes_len), r):
                        possible_indexes = indexes[:]
                        for i in indices:
                            possible_indexes[i] = -1
                        if (data["key"], possible_indexes) in key_indexes_list:
                            if asyncio.iscoroutinefunction(listener):
                                await listener(data)
                            else:
                                listener(data)
            if event not in (self.listeners.get(trace_back=False) or {}):
                self.listeners.update(event, [])
            self.listeners.append("instant", { "listener": instant_hook_handler, "is_await": is_await })
        else:
            if is_agent_event:
                if event not in (self.agent_listeners.get(trace_back=False) or {}):
                    self.agent_listeners.update(event, [])
                self.agent_listeners.append(event, { "listener": listener, "is_await": is_await })
                return self.agent
            else:
                if event not in (self.listeners.get(trace_back=False) or {}):
                    self.listeners.update(event, [])
                self.listeners.append(event, { "listener": listener, "is_await": is_await })
                return self.agent

    def on_delta(self, listener: callable, *, is_await:bool=False, is_agent_event:bool=False):
        self.add("response:delta", listener, is_await=is_await, is_agent_event=is_agent_event)
        return self.agent

    def on_done(self, listener: callable, *, is_await:bool=False, is_agent_event:bool=False):
        self.add("response:done", listener, is_await=is_await, is_agent_event=is_agent_event)
        return self.agent

    def on_finally(self, listener: callable, *, is_await:bool=False, is_agent_event:bool=False):
        self.add("response:finally", listener, is_await=is_await, is_agent_event=is_agent_event)
        return self.agent

    def on_instant(self, listener: callable, *, is_await:bool=False, is_agent_event:bool=False):
        self.add("instant", listener, is_await=is_await, is_agent_event=is_agent_event)
        return self.agent
    
    def on_realtime(self, listener: callable, *, is_await:bool=False, is_agent_event:bool=False):
        self.agent.settings.set("use_instant", True)
        self.add("instant", listener, is_await=is_await, is_agent_event=is_agent_event)
        return self.agent
    
    async def call_event_listeners(self, event: str, data: any):
        event = event.replace(".", "->")
        listeners = self.listeners.get_trace_back() or {}
        if "*" in listeners:
            for listener_info in listeners["*"]:
                if asyncio.iscoroutinefunction(listener_info["listener"]):
                    if listener_info["is_await"]:
                        await listener_info["listener"](event , data)
                    else:
                        self.async_tasks.append(asyncio.create_task(listener_info["listener"](event, data)))
                else:
                    listener_info["listener"](event, data)
        if event in listeners:
            for listener_info in listeners[event]:
                if asyncio.iscoroutinefunction(listener_info["listener"]):
                    if listener_info["is_await"]:
                        await listener_info["listener"](data)
                    else:
                        self.async_tasks.append(asyncio.create_task(listener_info["listener"](data)))
                else:
                    listener_info["listener"](data)
        return self.agent

    async def _suffix(self, event:str, data: any):
        await self.call_event_listeners(event, data)
        if event == "response:finally":
            for async_task in self.async_tasks:
                await async_task
            self.async_tasks = []
            self.listeners.set({})

    def export(self):
        return {
            "prefix": None,
            "suffix": self._suffix,
            "alias": {
                "add_event_listener": { "func": self.add },
                "on_delta": { "func": self.on_delta },
                "on_done": { "func": self.on_done },
                "on_finally": { "func": self.on_finally },
                "on_instant": { "func": self.on_instant },
                "call_event_listeners": { "func": self.call_event_listeners },
            },
        }

def export():
    return ("EventListener", EventListener)