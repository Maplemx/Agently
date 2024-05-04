import asyncio
from .utils import ComponentABC

class EventListener(ComponentABC):
    def __init__(self, agent: object):
        self.agent = agent
        self.listeners = {}
        self.async_tasks = []

    def add(self, event:str, listener: callable, *, is_await:bool=False):
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append({ "listener": listener, "is_await": is_await })
        return self.agent

    def on_delta(self, listener: callable, *, is_await:bool=False):
        self.add("response:delta", listener, is_await=is_await)
        return self.agent

    def on_done(self, listener: callable, *, is_await:bool=False):
        self.add("response:done", listener, is_await=is_await)
        return self.agent

    def on_finally(self, listener: callable, *, is_await:bool=False):
        self.add("response:finally", listener, is_await=is_await)
        return self.agent

    async def _suffix(self, event:str, data: any):
        if event in self.listeners:
            for listener_info in self.listeners[event]:
                if asyncio.iscoroutinefunction(listener_info["listener"]):
                    if listener_info["is_await"]:
                        await listener_info["listener"](data)
                    else:
                        self.async_tasks.append(asyncio.create_task(listener_info["listener"](data)))
                else:
                    listener_info["listener"](data)
        if event == "response:finally":
            for async_task in self.async_tasks:
                await async_task
            self.listeners = {}

    def export(self):
        return {
            "prefix": None,
            "suffix": self._suffix,
            "alias": {
                "add_event_listener": { "func": self.add },
                "on_delta": { "func": self.on_delta },
                "on_done": { "func": self.on_done },
                "on_finally": { "func": self.on_finally },
            },
        }

def export():
    return ("EventListener", EventListener)