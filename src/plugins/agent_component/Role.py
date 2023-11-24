from .utils import ComponentABC
from Agently.utils import RuntimeCtxNamespace

class Role(ComponentABC):
    def __init__(self, agent: object):
        self.agent = agent
        self.role_runtime_ctx = RuntimeCtxNamespace("role", self.agent.agent_runtime_ctx)
        self.role_storage = self.agent.global_storage.table("role")

    def set_name(self, name: str):
        self.role_runtime_ctx.set("NAME", name)
        return self.agent

    def set(self, key: any, value: any=None):
        if value is not None:
            self.role_runtime_ctx.set(key, value)
        else:
            self.role_runtime_ctx.set("DESC", key)
        return self.agent

    def update(self, key: any, value: any=None):
        if value is not None:
            self.role_runtime_ctx.update(key, value)
        else:
            self.role_runtime_ctx.update("DESC", key)
        return self.agent        

    def append(self, key: any, value: any=None):
        if value is not None:
            self.role_runtime_ctx.append(key, value)
        else:
            self.role_runtime_ctx.append("DESC", key)
        return self.agent

    def extend(self, key: any, value: any=None):
        if value is not None:
            self.role_runtime_ctx.extend(key, value)
        else:
            self.role_runtime_ctx.extend("DESC", key)
        return self.agent

    def save(self, role_name: str=None):
        if role_name == None:
            role_name = self.role_runtime_ctx.get("NAME")
        if role_name != None and role_name != "":
            self.role_storage\
                .set(role_name, self.role_runtime_ctx.get())\
                .save()
            return self.agent
        else:
            raise Exception("[Agent Component: Role] Role attr 'NAME' must be stated before save. Use .set_role_name() to specific that.")

    def load(self, role_name: str):
        role_data = self.role_storage.get(role_name)
        for key, value in role_data.items():
            self.role_runtime_ctx.update(key, value)
        return self.agent

    def _prefix(self):
        return {
            "role": self.role_runtime_ctx.get(),
        }

    def export(self):
        return {
            "prefix": self._prefix,
            "suffix": None,
            "alias": {
                "set_role_name": { "func": self.set_name },
                "set_role": { "func": self.set },
                "update_role": { "func": self.update },
                "append_role": { "func": self.append },
                "extend_role": { "func": self.extend },
                "save_role": { "func": self.save },
                "load_role": { "func": self.load },
            },
        }

def export():
    return ("Role", Role)