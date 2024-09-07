from typing import TYPE_CHECKING
from .Repository import CheckpointRepository
from .Snapshot import Snapshot
from ..lib.constants import DEFAULT_CHECKPOINT_NAME
from ..utils.runner import run_async

if TYPE_CHECKING:
    from .State import RuntimeState

class Checkpoint:
  """ Checkpoint 管理逻辑，包含快照数据存储、回溯、恢复等 """

  def __init__(self, checkpoint_id, repository=CheckpointRepository()) -> None:
    self.checkpoint_id = checkpoint_id
    self.repository: CheckpointRepository = repository
    self.active_snapshot: Snapshot = None

  def save(self, state: 'RuntimeState', name=DEFAULT_CHECKPOINT_NAME, time=None, **args):
    """将某个状态存储到快照记录中"""
    return run_async(self.save_async(state=state, name=name, time=time,  **args))

  async def save_async(self, state: 'RuntimeState', name=DEFAULT_CHECKPOINT_NAME, time=None):
    """将某个状态存储到快照记录中"""
    snapshot = Snapshot(name=name, state=state, time=time)
    await self.repository.save(checkpoint_id=self.checkpoint_id, name=name, data=snapshot.export())
    return self
  
  def remove(self, name=DEFAULT_CHECKPOINT_NAME):
    return run_async(self.remove_async(name=name))

  async def remove_async(self, name=DEFAULT_CHECKPOINT_NAME):
    """删除指定的快照存储"""
    await self.repository.remove(checkpoint_id=self.checkpoint_id, name=name)
    return self

  def rollback(self, name=DEFAULT_CHECKPOINT_NAME, silence=False, **args):
    """ 回滚到指定checkpoint """
    run_async(self.rollback_async(name=name, silence=silence, **args))

  async def rollback_async(self, name=DEFAULT_CHECKPOINT_NAME, silence=False):
    """ 回滚到指定checkpoint """
    snapshot_raw_data = await self.repository.get(self.checkpoint_id, name)
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
