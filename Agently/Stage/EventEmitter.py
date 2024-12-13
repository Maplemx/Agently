from .Stage import Stage

class EventEmitter:
    def __init__(self, private_max_workers=None, max_concurrent_tasks=None, on_error=None):
        self._listeners = {}
        self._once = {}
        self._stage = Stage(
            private_max_workers=private_max_workers,
            max_concurrent_tasks=max_concurrent_tasks,
            on_error=on_error,
            is_daemon=True,
        )
    
    def add_listener(self, event, listener):
        if event not in self._listeners:
            self._listeners.update({ event: [] })
        if listener not in self._listeners[event]:
            self._listeners[event].append(listener)
        return listener
    
    def remove_listener(self, event, listener):
        if event in self._listeners and listener in self._listeners[event]:
            self._listeners[event].remove(listener)

    def remove_all_listeners(self, event_list):
        if isinstance(event_list, str):
            event_list = [event_list]
        for event in event_list:
            self._listeners.update({ event: [] })

    def on(self, event, listener):
        return self.add_listener(event, listener)
    
    def off(self, event, listener):
        return self.remove_listener(event, listener)

    def once(self, event, listener):
        if event not in self._once:
            self._once.update({ event: [] })
        if listener not in self._listeners[event] and listener not in self._once[event]:
            self._once[event].append(listener)
        return listener
    
    def listener_count(self, event):
        return len(self._listeners[event]) + len(self._once[event])
        
    def emit(self, event, *args, **kwargs):
        listeners_to_execute = []
        if event in self._listeners:
            for listener in self._listeners[event]:
                listeners_to_execute.append((listener, args, kwargs))
        if event in self._once:
            for listener in self._once[event]:
                listeners_to_execute.append((listener, args, kwargs))
            self._once.update({ event: [] })
        for listener, args, kwargs in listeners_to_execute:
            self._stage.go(listener, *args, **kwargs)
        return len(listeners_to_execute)