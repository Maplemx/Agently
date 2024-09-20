from collections import deque
from typing import List
from ..utils.chunk_helper import deep_copy_simply

class RuntimeBranchState:
  """某个分支的运行时状态"""
  def __init__(self, **args) -> None:
    self.id = args.get('id')
    # 恢复各 chunk 的运行状态
    self.chunk_status = args.get('chunk_status', {})
    self.executing_ids: List[str] = args.get('executing_ids', [])
    self.visited_record: List[str] = args.get('visited_record', [])
    # 总运行状态
    self.running_status = args.get('running_status', 'idle')
    # 快队列
    self.running_queue = deque(args.get('running_queue', []))
    # 慢队列
    self.slow_queue = deque(args.get('slow_queue', []))

  def update_chunk_status(self, chunk_id, status):
    if status not in ['idle', 'success', 'running', 'error', 'pause']:
      return
    self.chunk_status[chunk_id] = status

  def get_chunk_status(self, chunk_id):
    return self.chunk_status.get(chunk_id)
  
  def export(self):
    return deep_copy_simply({
      'id': self.id,
      'executing_ids': self.executing_ids,
      'chunk_status': self.chunk_status,
      'visited_record': self.visited_record,
      'running_status': self.running_status,
      'running_queue': list(self.running_queue),
      'slow_queue': list(self.slow_queue)
    })
