from typing import List
from ..utils.chunk_helper import deep_copy_simply

class RuntimeBranchState:
  """Runtime 的某个时刻的执行快照，通过叠加 action，可生成新的 snapshot"""
  def __init__(self, id: str, **args) -> None:
    self.id = id
    self.slow_tasks: List['RuntimeBranchState'] = args.get('slow_tasks', [])
    self.executing_ids: List[str] = args.get('executing_ids', [])
    self.visited_record: List[str] = args.get('visited_record', [])
    # 总运行状态
    self.running_status = args.get('running_status', 'idle')
  
  def create_slow_task(self, chunk) -> 'RuntimeBranchState':
    snapshot_unit = RuntimeBranchState(id=chunk['id'])
    self.slow_tasks.append(snapshot_unit)
    return snapshot_unit
  
  def export(self):
    return deep_copy_simply({
      'id': self.id,
      'slow_tasks': self.slow_tasks,
      'executing_ids': self.executing_ids,
      'visited_record': self.visited_record,
      'running_status': self.running_status
    })
