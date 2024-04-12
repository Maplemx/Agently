class Store:
  def __init__(self, init_schema = {}) -> None:
    self.store = init_schema.copy()

  def set(self, name: str, data: any):
    self.store[name] = data
  
  def set_with_dict(self, data: dict):
    self.store.update(data)
  
  def remove(self, name: str):
    if name in self.store:
      del self.store[name]
    return self

  def get(self, name: str, default = None):
    return self.store.get(name) or default
  
  def get_all(self):
    return self.store.deepcopy()