from typing import TYPE_CHECKING
from .Repository import CheckpointRepository
from .Snapshot import Snapshot
from ..lib.constants import DEFAULT_CHECKPOINT_NAME
from ..utils.runner import run_async

if TYPE_CHECKING:
    from .State import RuntimeState

class Checkpoint:
  """ Checkpoint 管理逻辑，包含快照数据存储、回溯、恢复等 """

  def __init__(self, checkpoint_id, repository=CheckpointRepository(), default_snapshot_name: str=None) -> None:
    # 默认存储的快照名
    self.default_snapshot_name = default_snapshot_name or DEFAULT_CHECKPOINT_NAME
    self.checkpoint_id = checkpoint_id
    self.repository: CheckpointRepository = repository
    self.active_snapshot: Snapshot = None
    self._disabled = False
  
  def use(self, name: str):
    """使用指定的快照名（存储、回滚、删除默认都会使用该快照名）"""
    self.default_snapshot_name = name
    return self
  
  def disable(self):
    self._disabled = True
    return self

  def save(self, state: 'RuntimeState', name=None, time=None, **args):
    """将某个状态存储到快照记录中"""
    if self._disabled:
      return self
    return run_async(self.save_async(state=state, name=name, time=time,  **args))

  async def save_async(self, state: 'RuntimeState', name=None, time=None):
    """将某个状态存储到快照记录中"""
    if self._disabled:
      return self
    snapshot_name = name or self.default_snapshot_name
    snapshot = Snapshot(name=snapshot_name, state=state, time=time)
    await self.repository.save(checkpoint_id=self.checkpoint_id, name=snapshot_name, data=snapshot.export())
    return self
  
  def remove(self, name=None):
    if self._disabled:
      return self
    snapshot_name = name or self.default_snapshot_name
    return run_async(self.remove_async(name=snapshot_name))

  async def remove_async(self, name=None):
    """删除指定的快照存储"""
    if self._disabled:
      return self
    snapshot_name = name or self.default_snapshot_name
    await self.repository.remove(checkpoint_id=self.checkpoint_id, name=snapshot_name)
    return self

  def rollback(self, name=None, silence=False, **args):
    """回滚到指定checkpoint"""
    if self._disabled:
      return self
    snapshot_name = name or self.default_snapshot_name
    run_async(self.rollback_async(name=snapshot_name, silence=silence, **args))

  async def rollback_async(self, name=None, silence=False):
    """回滚到指定checkpoint"""
    if self._disabled:
      return self
    snapshot_name = name or self.default_snapshot_name
    snapshot_raw_data = await self.repository.get(checkpoint_id=self.checkpoint_id, name=snapshot_name)
    if not snapshot_raw_data:
      # 静默态，无需抛错
      if silence:
        return self
      raise ValueError(
          f'Attempt to roll back to a non-existent checkpoint record named "{name}".')

    self.active_snapshot = Snapshot(**snapshot_raw_data)
    return self
  
  def get_active_snapshot(self):
    """返回当前激活的快照"""
    return self.active_snapshot
