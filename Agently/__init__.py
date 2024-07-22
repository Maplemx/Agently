#import nest_asyncio
from .Request import Request
from .Agent import AgentFactory
from .Facility import FacilityManager
from .WebSocket import WebSocketServer, WebSocketClient
from .Workflow import Workflow, Schema as WorkflowSchema
from ._global import global_plugin_manager, global_settings, global_storage, global_tool_manager, global_websocket_server
from .utils import *

#nest_asyncio.apply()
def create_agent(*args, **kwargs):
    return AgentFactory().create_agent(*args, **kwargs)

facility = FacilityManager()
lib = facility

set_settings = global_settings.set

def set_compatible(compatible_version: str):
    if isinstance(compatible_version, str):
        compatible_version = int(compatible_version.replace(".", ""))
    set_settings("compatible_version", compatible_version)
    # auto switch settings by compatible version
    if compatible_version <= 3320:
        set_settings("storage_type", "FileStorage")
        set_settings("storage.FileStorage.path", "./.Agently")

def register_plugin(module_name:str, plugin_name: str, plugin: callable):
    global_plugin_manager.register(module_name, plugin_name, plugin)
    facility.refresh_plugins()

def set_plugin_settings(module_name: str, plugin_name: str, key: str, value: any):
    global_plugin_manager.set_settings(f"plugin_settings.{ module_name }.{ plugin_name }", key, value)