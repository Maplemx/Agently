from collections import deque
from typing import List
from ..utils.chunk_helper import deep_copy_simply

class RuntimeBranchState:
  """Runtime 的某个时刻的执行快照，通过叠加 action，可生成新的 snapshot"""
  def __init__(self, **args) -> None:
    self.id = args.get('id')
    self.slow_tasks: List['RuntimeBranchState'] = [
      RuntimeBranchState(**slow_task_value)
      for slow_task_value in args.get('slow_tasks', [])
    ]
    # 恢复各 chunk 的运行状态
    self.chunk_status = args.get('chunk_status', {})
    self.executing_ids: List[str] = args.get('executing_ids', [])
    self.visited_record: List[str] = args.get('visited_record', [])
    # 总运行状态
    self.running_status = args.get('running_status', 'idle')
    self.running_queue = deque(args.get('running_queue', []))
  
  def create_slow_task(self, chunk) -> 'RuntimeBranchState':
    snapshot_unit = RuntimeBranchState(id=chunk['id'])
    self.slow_tasks.append(snapshot_unit)
    return snapshot_unit
  
  def update_chunk_status(self, chunk_id, status):
    if status not in ['idle', 'success', 'running', 'error', 'pause']:
      return
    self.chunk_status[chunk_id] = status

  def get_chunk_status(self, chunk_id):
    return self.chunk_status.get(chunk_id)
  
  def export(self):
    print(self.running_queue)
    # 将分支状态实例导出状态原值
    slow_task_value = []
    for slow_task in self.slow_tasks:
      slow_task_value.append(slow_task.export())
    return deep_copy_simply({
      'id': self.id,
      'slow_tasks': slow_task_value,
      'executing_ids': self.executing_ids,
      'chunk_status': self.chunk_status,
      'visited_record': self.visited_record,
      'running_status': self.running_status,
      'running_queue': list(self.running_queue)
    })
