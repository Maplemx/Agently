from Agently.utils import RuntimeCtx

class RoleManager(object):
    def __init__(self, *, storage: object, plugin_manager: object):
        self.storage = storage.table("role")
        self.plugin_manager = plugin_manager
        self.role_runtime_ctx = RuntimeCtx()

    def name(self, name: str):
        self.role_runtime_ctx.set("NAME", name)
        return self

    def set(self, key: any, value: any=None):
        if value is not None:
            self.role_runtime_ctx.set(key, value)
        else:
            self.role_runtime_ctx.set("ROLE", key)
        return self

    def update(self, key: any, value: any=None):
        if value is not None:
            self.role_runtime_ctx.update(key, value)
        else:
            self.role_runtime_ctx.update("ROLE", key)
        return self     

    def append(self, key: any, value: any=None):
        if value is not None:
            self.role_runtime_ctx.append(key, value)
        else:
            self.role_runtime_ctx.append("ROLE", key)
        return self

    def extend(self, key: any, value: any=None):
        if value is not None:
            self.role_runtime_ctx.extend(key, value)
        else:
            self.role_runtime_ctx.extend("ROLE", key)
        return self

    def save(self, role_name: str=None):
        if role_name == None:
            role_name = self.role_runtime_ctx.get("NAME")
        if role_name != None and role_name != "":
            self.storage\
                .set(role_name, self.role_runtime_ctx.get())\
                .save()
            self.role_runtime_ctx.empty()
            return self
        else:
            raise Exception("[Facility: RoleMananger] Role attr 'NAME' must be stated before save.")

    def get(self, role_name: str):
        return self.storage.get(role_name)

def export():
    return ("role_manager", RoleManager)