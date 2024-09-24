import time as time_raw
from typing import TYPE_CHECKING, Union
from ..utils.chunk_helper import deep_copy_simply

if TYPE_CHECKING:
    from .State import RuntimeState

class Snapshot:
  """主要负责单个 RuntimeState 的静态化挂载及管理逻辑"""

  def __init__(self, name: str, state: Union['RuntimeState', dict], time: int = None) -> None:
    self.name = name
    self.state_schema = state if isinstance(state, dict) else state.export()
    self.time = time or time_raw.time()
  
  def get_state_val(self, keys_with_dots: str):
    """获取指定状态值"""
    keys = keys_with_dots.split('.')
    pointer = self.state_schema
    for key in keys:
      if not pointer or key not in pointer:
        return None
      pointer = pointer.get(key)
    return deep_copy_simply(pointer)

  def export(self) -> dict:
     return deep_copy_simply({
        'name': self.name,
        'state': self.state_schema,
        'time': self.time
     })