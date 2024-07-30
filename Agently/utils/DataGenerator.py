import queue

class DataGenerator:
    def __init__(self):
        self.queue = queue.Queue()
    
    def get_generator(self):
        while True:
            data = self.queue.get()
            if data == "$END$":
                break
            else:
                yield data
    
    def add(self, data):
        self.queue.put(data)
        return self
    
    def end(self):
        self.queue.put("$END$")