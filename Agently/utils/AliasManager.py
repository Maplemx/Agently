import json
import inspect
import asyncio

class AliasManager(object):
    def __init__(self, target: object):
        self.target = target
        self.alias_name_list = []
        self.alias_details = {}

    def register(self, alias_name: str, alias_func: callable, *, return_value: bool=False, agent_component_name: str=None):
        if alias_name in self.alias_name_list:
            raise Exception(f"[Alias Manager] alias_name '{ alias_name }' has already been registered.")
        if return_value:
            setattr(self.target, alias_name, alias_func)
        else:
            if asyncio.iscoroutinefunction(alias_func):
                async def _alias_func(*args, **kwargs):
                    await alias_func(*args, **kwargs)
                    return self.target
                setattr(self.target, alias_name, _alias_func)
            else:
                def _alias_func(*args, **kwargs):
                    alias_func(*args, **kwargs)
                    return self.target
                setattr(self.target, alias_name, _alias_func)
        self.alias_name_list.append(alias_name)
        self.alias_details.update({ alias_name: { "func": alias_func, "return_value": return_value, "agent_component": agent_component_name } })
        return self

    def empty_alias(self):
        self.alias_name_list = []
        self.alias_details = {}
        return self

    def get_alias_info(self, *, group_by: str=None):
        result = {}
        if group_by == "agent_component":
            for alias_name, alias_info in self.alias_details.items():
                if alias_info["agent_component"] == None:
                    agent_component_name = "Unnamed"
                else:
                    agent_component_name = alias_info["agent_component"]
                if agent_component_name not in result:
                    result[agent_component_name] = {}
                result[agent_component_name][alias_name] = { "paramaters": [] }
                alias_func_info = inspect.signature(alias_info["func"])
                for name, meta in alias_func_info.parameters.items():
                    result[agent_component_name][alias_name]["paramaters"].append(str(meta.name))
                    result[agent_component_name][alias_name]["is_return_value"] = alias_info["return_value"]
                    result[agent_component_name][alias_name]["docstring"] = str(alias_info["func"].__doc__)
        else:
            for alias_name, alias_info in self.alias_details.items():
                result[alias_name] = { "paramaters": [] }
                alias_func_info = inspect.signature(alias_info["func"])
                for name, meta in alias_func_info.parameters.items():
                    result[alias_name]["paramaters"].append(str(meta.name))
                result[alias_name]["is_return_value"] = alias_info["return_value"]
                result[alias_name]["docstring"] = str(alias_info["func"].__doc__)
                result[alias_name]["agent_component"] = alias_info["agent_component"]
        return result

    def print_alias_info(self, *, group_by: str=None):
        print(json.dumps(self.get_alias_info(group_by=group_by), indent=4, ensure_ascii=False))