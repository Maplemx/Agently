from typing import Dict, TYPE_CHECKING
from .BranchState import RuntimeBranchState

if TYPE_CHECKING:
    from .Snapshot import Snapshot

CURRENT_STATE_VERSION = 1

class RuntimeState:
  """整个 workflow 的运行时状态"""

  def __init__(self, **args) -> None:
    if args.get('v') and args.get('v') != CURRENT_STATE_VERSION:
      raise ValueError(f'The state data of version {args.get("v")} cannot be used on the checkpoint management logic of version {CURRENT_STATE_VERSION}.')
    # schema 版本
    self.v = CURRENT_STATE_VERSION
    self.workflow_id = args.get('workflow_id')
    # 分支决策逻辑
    self.branches_state: Dict[str, RuntimeBranchState] = args.get(
        'branches_state', {})
    # 各 chunk 依赖数据
    self.chunks_dep_state = args.get('chunks_dep_state', {})
    # 各 chunk 附加数据（如 Loop chunk 的 State 数据）
    self.chunks_extra_data = args.get('chunks_extra_data', {})
    # 总运行状态
    self.running_status = args.get('running_status', 'idle')
    # 运行数据
    self.user_store = args.get('user_store')
    self.sys_store = args.get('sys_store')
    self.restore_mode = False
  
  def restore_from_snapshot(self, snapshot: 'Snapshot') -> 'RuntimeState':
    """从指定表述结构中恢复"""
    schema = snapshot.export().get('state')
    # 版本校验
    if schema.get('v') and schema.get('v') != CURRENT_STATE_VERSION:
      raise ValueError(
          f'The state data of version {schema.get("v")} cannot be used on the checkpoint management logic of version {CURRENT_STATE_VERSION}.')
    self.workflow_id = schema.get('workflow_id')

    # 恢复挂载实例化的 branch_state
    branches_state = schema.get('branches_state')
    self.branches_state = {}
    for entry_id in branches_state:
      self.branches_state[entry_id] = RuntimeBranchState(**branches_state[entry_id])
    
    # 恢复依赖数据
    self.chunks_dep_state = schema.get('chunks_dep_state')
    # 恢复运行状态
    self.running_status = schema.get('running_status')
    # 恢复用户 store
    self.user_store = self.user_store.__class__(schema.get('user_store'))
    # 恢复系统 store
    self.sys_store = self.sys_store.__class__(schema.get('sys_store'))
    # 恢复模式
    self.restore_mode = True
    return self

  def update(self, chunks_dep_state: dict = {}):
    # 各 chunk 依赖数据
    self.chunks_dep_state = chunks_dep_state or {}

  def create_branch_state(self, chunk) -> RuntimeBranchState:
    self.branches_state[chunk['id']] = RuntimeBranchState(id=chunk['id'])
    return self.branches_state[chunk['id']]
  
  def get_branch_state(self, chunk) -> RuntimeBranchState:
    return self.branches_state.get(chunk['id'])
  
  def export(self):
    # 将分支状态实例导出状态原值
    branches_state_value = {}
    for id in self.branches_state:
      branches_state_value[id] = self.branches_state[id].export()
    # 返回快照数据
    return {
      'v': self.v,
      'workflow_id': self.workflow_id,
      'branches_state': branches_state_value,
      'chunks_dep_state': self.chunks_dep_state,
      'running_status': self.running_status,
      'user_store': self.user_store.get_all(),
      'sys_store': self.sys_store.get_all()
    }
