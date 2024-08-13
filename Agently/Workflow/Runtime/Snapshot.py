from typing import TYPE_CHECKING, Dict
from ..utils.chunk_helper import deep_copy_simply
from .BranchState import RuntimeBranchState

if TYPE_CHECKING:
    from .Action import RuntimeAction

class RuntimeSnapshot:
  """Runtime 的某个时刻的执行快照，通过叠加 action，可生成新的 snapshot"""

  def __init__(self, chunks_dep_state: dict = {}) -> None:
    # 分支决策逻辑
    self.branchs_state: Dict[str, RuntimeBranchState] = {}
    # 各 chunk 依赖数据
    self.chunks_dep_state = chunks_dep_state or {}
  
  def update(self, chunks_dep_state: dict = {}):
    # 各 chunk 依赖数据
    self.chunks_dep_state = chunks_dep_state or {}

  def create_branch_state(self, chunk) -> RuntimeBranchState:
    self.branchs_state[chunk['id']] = RuntimeBranchState(id=chunk['id'])
    return self.branchs_state[chunk['id']]
  
  def get_snapshot_unit(self, id) -> RuntimeBranchState:
    return self.branchs_state.get(id)

  def export(self, type="json"):
    """导出为描述文件"""
    pass

  def update_with_action(self, action: 'RuntimeAction') -> 'RuntimeSnapshot':
    """通过迭代一个 action，产生新的 snapshot """
    shadow_snapshot = self.copy()
    action.execute_on(shadow_snapshot)
    return shadow_snapshot
