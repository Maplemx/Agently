import queue

class DataGeneratorTimeoutException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"\n[Data Generator] Error: { str(self.message) }"

class DataGeneratorEvent:
    def __init__(self, data_generator: "DataGenerator"):
        self.data_generator = data_generator
        self.handlers = {}
    
    def emit(self, event:str, data:any):
        self.data_generator.add({
            "event": event,
            "data": data,
        })
        return self
    
    def on(self, event:str, handler:callable):
        if event not in self.handlers:
            self.handlers.update({ event: [] })
        self.handlers[event].append(handler)
        return self
    
    def clean(self, event:str):
        if event in self.handlers:
            del self.handlers[event]
        return self

class DataGenerator:
    def __init__(self, *, timeout:int=None, allow_timeout:bool=False):
        self.queue = queue.Queue()
        self.timeout = timeout
        self.allow_timeout = allow_timeout
        self.event = DataGeneratorEvent(self)
    
    def start(self):
        end_flag = False
        while True:
            try:
                if self.timeout:
                    data = self.queue.get(timeout=self.timeout)
                else:
                    data = self.queue.get()
                if data == "$END$":
                    self.queue = queue.Queue()
                    break
                else:
                    if "event" in data:
                        if data["event"] in self.event.handlers:
                            for handler in self.event.handlers[data["event"]]:
                                result = handler(data["data"])
                                if "yield" in result:
                                    yield result["yield"]
                                if "end" in result and result["end"] == True:
                                    self.queue = queue.Queue()
                                    end_flag = True
                            if end_flag:
                                break
                    else:
                        yield data
            except queue.Empty:
                self.queue = queue.Queue()
                if self.allow_timeout:
                    break
                else:
                    raise DataGeneratorTimeoutException(f"Data generator timeout (wait { self.timeout } seconds). Use `.end()` to put an end to the data queue before `.start()`.")
    
    def add(self, data):
        self.queue.put(data)
        return self
        
    def end(self):
        self.queue.put("$END$")