from typing import List

class RuntimeBranchState:
  """Runtime 的某个时刻的执行快照，通过叠加 action，可生成新的 snapshot"""
  def __init__(self, id: str) -> None:
    self.id = id
    self.slow_tasks: List['RuntimeBranchState'] = []
    self.executing_ids: List[str] = []
    self.visited_record: List[str] = []
  
  def create_slow_task(self, chunk) -> 'RuntimeBranchState':
    snapshot_unit = RuntimeBranchState(id=chunk['id'])
    self.slow_tasks.append(snapshot_unit)
    return snapshot_unit
