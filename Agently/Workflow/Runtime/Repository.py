from typing import List
from Agently.utils import PluginManager, StorageDelegate, ToolManager, RuntimeCtx
checkpoint_plugin_manager = PluginManager()
checkpoint_tool_manager = ToolManager()
checkpoint_settings = RuntimeCtx()

class CheckpointRepository:
  def __init__(self, storage = None) -> None:
    self.storage = storage or StorageDelegate(
      db_name="checkpoint",
      plugin_manager=checkpoint_plugin_manager,
      settings=checkpoint_settings
    )

  async def save(self, workflow_id, name: str, data: any):
    self.storage.set(table_name=workflow_id, key=name, value=data)
    return self

  async def remove(self, workflow_id, name: str):
    self.storage.remove(table_name=workflow_id, key=name)
    return self

  async def get(self, workflow_id, name: str):
    return self.storage.get(workflow_id, key=name)

  async def get_all(self, workflow_id, names: List[str] = None):
    return self.storage.get_all(workflow_id, keys=names)
