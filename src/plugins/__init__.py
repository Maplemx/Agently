import os
import sys
import json
import importlib
from Agently.utils import find_json

def install_plugins(plugin_manager, tool_manager, settings):
    dir_path = os.path.dirname(os.path.abspath(__file__))
    for item in os.listdir(dir_path):
        if os.path.exists(f"{ dir_path }/{ item }/__init__.py"):
            module_plugins = importlib.import_module(f".{ item }", package = __package__)
            if not hasattr(module_plugins, "export"):
                raise Exception(f"[Plugin Manager] Function 'export' must be stated in '__init__.py' file in module plugin dir: { dir_path }/{ item }")
            module_plugin_export = getattr(module_plugins, "export")()
            module_plugin_list = module_plugin_export[0]
            module_default_settings = module_plugin_export[1]
            orders = module_plugin_export[2] if len(module_plugin_export) > 2 else None
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
            if orders and item == "agent_component":
                agent_component_list = plugin_manager.get_agent_component_list()
                for process_type in orders:
                    order_list = orders[process_type].split(",")
                    current_mode = "firstly"
                    order_settings = {
                        "firstly": [],
                        "normally": [],
                        "finally": [],
                    }
                    for agent_component_name in order_list:
                        agent_component_name = agent_component_name.replace(" ", "")
                        if agent_component_name == "...":
                            current_mode = "finally"
                        elif agent_component_name in agent_component_list:
                            order_settings[current_mode].append(agent_component_name)
                    ordered_agent_component_list = order_settings["firstly"].copy()
                    ordered_agent_component_list.extend(order_settings["finally"].copy())
                    for agent_component_name in agent_component_list:
                        if agent_component_name not in ordered_agent_component_list:
                            order_settings["normally"].append(agent_component_name)
                    settings.set(f"plugin_settings.agent_component.orders.{ process_type }", order_settings)
    for tool_package_name, ToolPackageClass in plugin_manager.plugins_runtime_ctx.get("tool", {}).items():
        tool_package = ToolPackageClass(tool_manager)
        for tool_name, tool_info in tool_package.export().items():
            if "desc" not in tool_info:
                raise Exception(f"[Plugin] Tool '{ tool_name }' in tool package '{ tool_package_name }' must export key 'desc'.")
            if "args" not in tool_info or not isinstance(tool_info["args"], dict):
                raise Exception(f"[Plugin] Tool '{ tool_name }' in tool package '{ tool_package_name }' must export key 'args', set the value as {{}} if need no args.")
            if "func" not in tool_info or not callable(tool_info["func"]):
                raise Exception(f"[Plugin] Tool '{ tool_name }' in tool package '{ tool_package_name }' must export key 'func'.")
            tool_manager.register(
                tool_name = tool_name,
                desc = tool_info["desc"],
                args = tool_info["args"],
                func = tool_info["func"],
                require_proxy = tool_info["require_proxy"] if "require_proxy" in tool_info else False,
                categories = tool_info["categories"] if "categories" in tool_info else None
            )

def install(Agently):
    install_plugins(Agently.global_plugin_manager, Agently.global_tool_manager, Agently.global_settings)
    Agently.facility.refresh_plugins()

def install_to_agent(agent):
    install_plugins(agent.plugin_manager, agent.tool_manager, agent.settings)
    agent.refresh_plugins()