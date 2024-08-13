from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .Snapshot import RuntimeSnapshot

class RuntimeAction:
  """运行时变更行为，snapshot + action = new_snapshot"""
  def __init__(self) -> None:
    pass

  def execute_on(self, snapshot: 'RuntimeSnapshot'):
    """在指定的快照上执行变更行为"""
    pass
