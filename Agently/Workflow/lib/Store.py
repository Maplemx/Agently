"""
import copy

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
  
  def remove_all(self):
    self.store = {}
    return self

  def get(self, name: str, default = None):
    return self.store.get(name) or default
  
  def get_all(self):
    return copy.deepcopy(self.store)
"""

import Agently.utils.DataOps as DataOps

class Store(DataOps):
  def __init__(self, init_schema = None):
    super().__init__(target_data = init_schema)
    self.store = self.target_data
    self.remove_all = self.empty
    self.set_with_dict = self.update_by_dict
    self.get_all = lambda: self.get()