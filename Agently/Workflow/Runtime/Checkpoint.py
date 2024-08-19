from typing import TYPE_CHECKING
from .Repository import CheckpointRepository
from .Snapshot import Snapshot
from ..lib.constants import DEFAULT_CHECKPOINT_NAME

if TYPE_CHECKING:
    from .State import RuntimeState

class Checkpoint:
  """ Checkpoint 管理逻辑，包含快照数据存储、回溯、恢复等 """

  def __init__(self, workflow_id, repository=CheckpointRepository()) -> None:
    self.workflow_id = workflow_id
    self.repository: CheckpointRepository = repository
    self.active_snapshot: Snapshot = None

  async def save(self, state: 'RuntimeState', name=DEFAULT_CHECKPOINT_NAME, time=None):
    """将某个状态存储到快照记录中"""
    snapshot = Snapshot(name=name, state=state, time=time)
    await self.repository.save(workflow_id=self.workflow_id, name=name, data=snapshot.export())
    return self

  async def rollback(self, name=DEFAULT_CHECKPOINT_NAME, silence=False):
    snapshot_raw_data = await self.repository.get(self.workflow_id, name)
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
