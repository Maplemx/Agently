from .utils import FacilityABC
from Agently.utils import RuntimeCtx

class RoleManager(FacilityABC):
    def __init__(self, *, storage: object, plugin_manager: object, settings: object):
        self.storage = storage.table("role")
        self.plugin_manager = plugin_manager
        self.role_runtime_ctx = RuntimeCtx()

    def set_id(self, role_id: str):
        self.role_runtime_ctx.set("$ID", role_id)
        return self

    def set(self, key: any, value: any=None):
        if value is not None:
            self.role_runtime_ctx.set(key, value)
        else:
            self.role_runtime_ctx.set("DESC", key)
        return self

    def update(self, key: any, value: any=None):
        if value is not None:
            self.role_runtime_ctx.update(key, value)
        else:
            self.role_runtime_ctx.update("DESC", key)
        return self     

    def append(self, key: any, value: any=None):
        if value is not None:
            self.role_runtime_ctx.append(key, value)
        else:
            self.role_runtime_ctx.append("DESC", key)
        return self

    def extend(self, key: any, value: any=None):
        if value is not None:
            self.role_runtime_ctx.extend(key, value)
        else:
            self.role_runtime_ctx.extend("DESC", key)
        return self

    def save(self, role_id: str=None):
        role_id = role_id or self.role_runtime_ctx.get("$ID")
        if role_id is None or role_id == "":
            raise Exception("[Facility: RoleMananger] Role ID must be stated before save. Use .set_id() to specific it or pass role id into .save(<role_id>).")
        self.storage.set(role_id, self.role_runtime_ctx.get()).save()
        self.role_runtime_ctx.empty()
        return self

    def get(self, role_id: str):
        return self.storage.get(role_id)

def export():
    return ("role_manager", RoleManager)