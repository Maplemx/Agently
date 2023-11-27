import os
import sys
import json
import importlib
from Agently.utils import find_json

def install_plugins(plugin_manager, settings):
    dir_path = os.path.dirname(os.path.abspath(__file__))
    for item in os.listdir(dir_path):
        if os.path.exists(f"{ dir_path }/{ item }/__init__.py"):
            module_plugins = importlib.import_module(f".{ item }", package = __package__)
            if not hasattr(module_plugins, "export"):
                raise Exception(f"[Plugin Manager] Function 'export' must be stated in '__init__.py' file in module plugin dir: { dir_path }/{ item }")
            module_plugin_export = getattr(module_plugins, "export")()
            module_plugin_list = module_plugin_export[0]
            module_default_settings = module_plugin_export[1]
            prefix_orders = module_plugin_export[2] if len(module_plugin_export) > 2 else None
            try:
                for plugin_info in module_plugin_list:
                    plugin_manager.register(plugin_info[0], plugin_info[1], plugin_info[2])
            except:
                raise Exception(f"[Plugin Manager] Function 'export' in '__init__.py' must return a list of tuple (<module name>, <plugin name>, <plugin method>).")
            if module_default_settings:
                #plugin_manager.update_settings(module_default_settings)
                for key, value in module_default_settings.items():
                    if isinstance(value, str) and value.lower() == "true":
                        module_default_settings[key] = True
                    if isinstance(value, str) and value.lower() == "false":
                        module_default_settings[key] = False
                    json_string = find_json(value)
                    if json_string != None and json_string != '':
                        module_default_settings[key] = json.loads(json_string)
                    settings.set(key, module_default_settings[key])
            if prefix_orders and item == "agent_component":
                agent_component_list = plugin_manager.get_agent_component_list()
                prefix_order_list = prefix_orders["orders"].split(",")
                current_mode = "firstly"
                prefix_order_settings = {
                    "firstly": [],
                    "normally": [],
                    "finally": [],
                }
                for prefix_order in prefix_order_list:
                    prefix_order = prefix_order.replace(" ", "")
                    if prefix_order == "...":
                        current_mode = "finally"
                    elif prefix_order in agent_component_list:
                        prefix_order_settings[current_mode].append(prefix_order)
                ordered_agent_component_list = prefix_order_settings["firstly"].copy()
                ordered_agent_component_list.extend(prefix_order_settings["finally"].copy())
                for agent_component_name in agent_component_list:
                    if agent_component_name not in ordered_agent_component_list:
                        prefix_order_settings["normally"].append(agent_component_name)
                settings.set(f"plugin_settings.agent_component.prefix_orders", prefix_order_settings)

def install(Agently):
    install_plugins(Agently.global_plugin_manager, Agently.global_settings)
    Agently.facility.refresh_plugins()

def install_to_agent(agent):
    install_plugins(agent.plugin_manager, agent.settings)
    agent.refresh_plugins()