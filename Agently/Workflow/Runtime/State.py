from typing import Dict
from .BranchState import RuntimeBranchState

class RuntimeState:
  """Runtime 的某个时刻的执行快照，通过叠加 action，可生成新的 snapshot"""

  def __init__(self, chunks_dep_state: dict, user_store, sys_store) -> None:
    # 分支决策逻辑
    self.branchs_state: Dict[str, RuntimeBranchState] = {}
    # 各 chunk 依赖数据
    self.chunks_dep_state = chunks_dep_state or {}
    # 总运行状态
    self.running_status = 'idle'
    # 运行数据
    self.user_store = user_store
    self.sys_store = sys_store

  def update(self, chunks_dep_state: dict = {}):
    # 各 chunk 依赖数据
    self.chunks_dep_state = chunks_dep_state or {}

  def create_branch_state(self, chunk) -> RuntimeBranchState:
    self.branchs_state[chunk['id']] = RuntimeBranchState(id=chunk['id'])
    return self.branchs_state[chunk['id']]
