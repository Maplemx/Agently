from typing import List
from Agently.utils import StorageDelegate
from Agently._global import global_plugin_manager, global_settings

class CheckpointRepository:
  def __init__(self, storage = None) -> None:
    self.storage = storage or StorageDelegate(
      db_name="checkpoint",
      plugin_manager=global_plugin_manager,
      settings=global_settings
    )

  async def save(self, checkpoint_id, name: str, data: any):
    self.storage.set(table_name=checkpoint_id, key=name, value=data)
    return self

  async def remove(self, checkpoint_id, name: str):
    self.storage.remove(table_name=checkpoint_id, key=name)
    return self

  async def get(self, checkpoint_id, name: str):
    return self.storage.get(checkpoint_id, key=name)

  async def get_all(self, checkpoint_id, names: List[str] = None):
    return self.storage.get_all(checkpoint_id, keys=names)
