#import nest_asyncio
try:
    import readline
except ImportError:
    import pyreadline as readline
from .Request import Request
from .Agent import AgentFactory
from .Facility import FacilityManager
from .WebSocket import WebSocketServer, WebSocketClient
from .Workflow import Workflow, Schema as WorkflowSchema
from .AppConnector import AppConnector
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

def attach_workflow(name: str, workflow: object):
    class AttachedWorkflow:
        def __init__(self, agent: object):
            self.agent = agent
            self.get_debug_status = lambda: self.agent.settings.get_trace_back("is_debug")
            self.settings = RuntimeCtxNamespace(f"plugin_settings.agent_component.{ name }", self.agent.settings)
        
        def start_workflow(self, init_inputs: dict=None, init_storage: dict={}):
            if not isinstance(init_storage, dict):
                raise Exception("[Workflow] Initial storage must be a dict.")
            init_storage.update({ "$agent": self.agent })
            return workflow.start(init_inputs, storage=init_storage)
        
        def export(self):
            return {
                "alias": {
                    name: { "func": self.start_workflow, "return_value": True },
                }
            }
    return register_plugin("agent_component", name, AttachedWorkflow)