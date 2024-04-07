import yaml as YAML
from .utils import ComponentABC
from Agently.utils import RuntimeCtxNamespace

class YAMLLoader(ComponentABC):
    def __init__(self, agent: object):
        self.agent = agent
        self.is_debug = lambda: self.agent.settings.get_trace_back("is_debug")
        self.settings = RuntimeCtxNamespace("plugin_settings.agent_component.YAMLReader", self.agent.settings)

    def transform_to_agently_style(self, target: any, variables: dict={}):
        if isinstance(target, dict):
            result = {}
            agently_tuple_list = [None, None]
            for key, value in target.items():
                if key == "$type":
                    agently_tuple_list[0] = self.transform_to_agently_style(value, variables=variables)
                elif key == "$desc":
                    agently_tuple_list[1] = self.transform_to_agently_style(value, variables=variables)
                else:
                    result.update({ key: self.transform_to_agently_style(value, variables=variables) })
            if agently_tuple_list[0] and agently_tuple_list[1]:
                result = (agently_tuple_list[0], agently_tuple_list[1])
            return result
        if isinstance(target, list):
            result = []
            for item in target:
                result.append(self.transform_to_agently_style(item, variables=variables))
            return result
        else:
            result = str(target)
            for key, value in variables.items():
                result = result.replace("${" + str(key) + "}", str(value))
            return result

    def load_yaml_prompt(self, *, path:str=None, yaml:str=None, use_agently_style:bool=True, variables:dict={}):
        # load yaml content
        yaml_dict = {}
        if variables:
            use_agently_style = True
        if not path and not yaml:
            raise Exception(f"[Agent Component: YAMLReader]: one parameter between `path` or `yaml` must be provided.")
        try:
            if path:
                with open(path, "r") as yaml_file:
                    yaml_dict = YAML.safe_load(yaml_file)
                    if use_agently_style:
                        yaml_dict = self.transform_to_agently_style(yaml_dict, variables=variables)
            else:
                yaml_dict = YAML.safe_load(yaml)
                if use_agently_style:
                    yaml_dict = self.transform_to_agently_style(yaml_dict, variables=variables)
        except Exception as e:
            raise Exception(f"[Agent Component: YAMLReader]: Error occured when read YAML from path '{ path }'.\nError: { str(e) }")
        # run agent alias
        agent_alias_list = dir(self.agent)
        for alias, value in yaml_dict.items():
            if alias in agent_alias_list:
                getattr(self.agent, alias)(value)
        return self.agent

    def export(self):
        return {
            "alias": {
                "load_yaml_prompt": { "func": self.load_yaml_prompt },
            }
        }

def export():
    return ("YAMLLoader", YAMLLoader)