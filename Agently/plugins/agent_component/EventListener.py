import types
import asyncio
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
        if event.startswith("realtime:"):
            event_data = event.replace(" ", "").split(":")
            hooks = event_data[1].replace("->", ".").split("&")
            hook_list = []
            for hook in hooks:
                hook_key_indexes = hook.split("?")
                hook_key = hook_key_indexes[0]
                hook_indexes = None
                if len(hook_key_indexes) > 1:
                    hook_indexes = hook_key_indexes[1].split(",")
                    for index, item in enumerate(hook_indexes):
                        if item.startswith("(") and item.endswith(")"):
                            items_in_item = item[1:-1].split("|")
                        else:
                            items_in_item = [item]
                        for i, value in enumerate(items_in_item):    
                            try:
                                items_in_item[i] = int(value)
                            except:
                                items_in_item[i] = None
                        hook_indexes[index] = items_in_item
                hook_list.append((hook_key, hook_indexes))
                async def realtime_hook_handler(data):
                    for hook in hook_list:
                        hook_key = hook[0]
                        hook_indexes = hook[1]
                        if (data["key"] == hook_key):
                            if hook_indexes and len(hook_indexes) <= len(data["indexes"]):
                                can_call = True
                                for position, hook_index in enumerate(hook_indexes):
                                    if hook_index != None and data["indexes"][position] not in hook_index:
                                        can_call = False
                                if can_call:
                                    if asyncio.iscoroutinefunction(listener):
                                        await listener(data)
                                    else:
                                        listener(data)
                            else:
                                if asyncio.iscoroutinefunction(listener):
                                    await listener(data)
                                else:
                                    listener(data)
                if event not in (self.listeners.get(trace_back=False) or {}):
                    self.listeners.update(event, [])
                self.listeners.append("realtime", { "listener": realtime_hook_handler, "is_await": is_await })
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

    def on_realtime(self, listener: callable, *, is_await:bool=False, is_agent_event:bool=False):
        self.add("realtime", listener, is_await=is_await, is_agent_event=is_agent_event)
        return self.agent
    
    async def call_event_listeners(self, event: str, data: any):
        event = event.replace(".", "->")
        listeners = self.listeners.get_trace_back() or {}
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
                "on_realtime": { "func": self.on_realtime },
                "call_event_listeners": { "func": self.call_event_listeners },
            },
        }

def export():
    return ("EventListener", EventListener)