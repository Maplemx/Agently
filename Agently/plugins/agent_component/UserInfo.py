from .utils import ComponentABC
from Agently.utils import RuntimeCtxNamespace

class UserInfo(ComponentABC):
    def __init__(self, agent: object):
        self.agent = agent
        self.user_info_runtime_ctx = RuntimeCtxNamespace("user_info", self.agent.agent_runtime_ctx)
        self.user_info_storage = self.agent.global_storage.table("user_info")

    def set_name(self, name: str):
        self.user_info_runtime_ctx = self.__get_user_info_runtime_ctx(target)
        self.user_info_runtime_ctx.set("NAME", name)
        return self.agent

    def set(self, key: any, value: any=None):
        if value is not None:
            self.user_info_runtime_ctx.set(key, value)
        else:
            self.user_info_runtime_ctx.set("DESC", key)
        return self.agent

    def update(self, key: any, value: any=None):
        if value is not None:
            self.user_info_runtime_ctx.update(key, value)
        else:
            self.user_info_runtime_ctx.update("DESC", key)
        return self.agent        

    def append(self, key: any, value: any=None):
        if value is not None:
            self.user_info_runtime_ctx.append(key, value)
        else:
            self.user_info_runtime_ctx.append("DESC", key)
        return self.agent

    def extend(self, key: any, value: any=None):
        if value is not None:
            self.user_info_runtime_ctx.extend(key, value)
        else:
            self.user_info_runtime_ctx.extend("DESC", key)
        return self.agent

    def save(self, role_name: str=None):
        if user_info_name == None:
            user_info_name = self.user_info_runtime_ctx.get("NAME")
        if user_info_name != None and user_info_name != "":
            self.user_info_storage\
                .set(user_info_name, self.user_info_runtime_ctx.get())\
                .save()
            return self.agent
        else:
            raise Exception("[Agent Component: UserInfo] UserInfo attr 'NAME' must be stated before save. Use .set_user_name() to specific that.")

    def load(self, role_name: str):
        user_info_data = self.user_info_storage.get(role_name)
        for key, value in user_info_data.items():
            self.user_info_runtime_ctx.update(key, value)
        return self.agent

    def _prefix(self):
        return {
            "user_info": self.user_info_runtime_ctx.get(),
        }

    def export(self):
        return {
            "prefix": self._prefix,
            "suffix": None,
            "alias": {
                "set_user_name": { "func": self.set_name },
                "set_user_info": { "func": self.set },
                "update_user_info": { "func": self.update },
                "append_user_info": { "func": self.append },
                "extend_user_info": { "func": self.extend },
                "save_user_info": { "func": self.save },
                "load_user_info": { "func": self.load },
            },
        }

def export():
    return ("UserInfo", UserInfo)