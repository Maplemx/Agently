import json
from typing import Dict
from .BranchState import RuntimeBranchState

class RuntimeState:
  """Runtime 的某个时刻的执行快照，通过叠加 action，可生成新的 snapshot"""

  def __init__(self, **args) -> None:
    self.workflow_id = args.get('workflow_id')
    # 分支决策逻辑
    self.branches_state: Dict[str, RuntimeBranchState] = args.get('branches_state', {})
    # 各 chunk 依赖数据
    self.chunks_dep_state = args.get('chunks_dep_state', {})
    # 总运行状态
    self.running_status = args.get('running_status', 'idle')
    # 分 chunk 运行状态
    self.chunk_status = args.get('chunk_status', {})
    # 运行数据
    self.user_store = args.get('user_store')
    self.sys_store = args.get('sys_store')

  def update(self, chunks_dep_state: dict = {}):
    # 各 chunk 依赖数据
    self.chunks_dep_state = chunks_dep_state or {}

  def create_branch_state(self, chunk) -> RuntimeBranchState:
    self.branches_state[chunk['id']] = RuntimeBranchState(id=chunk['id'])
    return self.branches_state[chunk['id']]
  
  def update_chunk_status(self, chunk_id, status):
    if status not in ['idle', 'success', 'running', 'error']:
      return
    self.chunk_status[chunk_id] = status
  
  def export(self):
    # 将分支状态实例导出状态原值
    branches_state_value = {}
    for id in self.branches_state:
      branches_state_value[id] = self.branches_state[id].export()
    # 返回快照数据
    return json.dumps({
      'workflow_id': self.workflow_id,
      'branches_state': branches_state_value,
      'chunks_dep_state': self.chunks_dep_state,
      'running_status': self.running_status,
      'chunk_status': self.chunk_status,
      'user_store': self.user_store.get_all(),
      'sys_store': self.sys_store.get_all()
    }, indent=2)