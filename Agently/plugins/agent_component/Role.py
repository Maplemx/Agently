from .utils import ComponentABC
from Agently.utils import RuntimeCtxNamespace

class Role(ComponentABC):
    def __init__(self, agent: object):
        self.agent = agent
        self.role_runtime_ctx = RuntimeCtxNamespace("role", self.agent.agent_runtime_ctx)
        self.role_storage = self.agent.global_storage.table("role")

    def set_id(self, role_id: str):
        self.role_runtime_ctx.set("$ID", role_id)
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

    def save(self, role_id: str=None):
        role_id = role_id or self.role_runtime_ctx.get("$ID")
        if role_id is None or role_id == "":
            raise Exception("[Agent Component: Role] Role ID must be stated before save. Use .set_role_id() to specific it or pass role id into .save_role(<role_id>).")
        self.role_storage.set(role_id, self.role_runtime_ctx.get()).save()
        return self.agent
            
    def load(self, role_id: str):
        role_id = role_id or self.role_runtime_ctx.get("$ID")
        if role_id is None or role_id == "":
            raise Exception("[Agent Component: Role] Role ID must be stated before load. Use .set_role_id() to specific it or pass role id into .load_role(<role_id>).")
        role_data = self.role_storage.get(role_id)
        for key, value in role_data.items():
            self.role_runtime_ctx.update(key, value)
        return self.agent

    def _prefix(self):
        role_settings = self.role_runtime_ctx.get() or {}
        if "$ID" in role_settings:
            del role_settings["$ID"]
        return {
            "role": role_settings,
        }

    def export(self):
        return {
            "prefix": self._prefix,
            "suffix": None,
            "alias": {
                "set_role_id": { "func": self.set_id },
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