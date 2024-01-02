from .RuntimeCtx import RuntimeCtx, RuntimeCtxNamespace

class ToolManager(object):
    def __init__(self, *, parent: object=None):
        self.parent = parent
        self.tool_runtime_ctx = RuntimeCtx(parent = self.parent.tool_runtime_ctx if self.parent else None)
        self.category_dict = {}
        self.tool_proxy = None
        self.runtime_cache = {}

    def set_tool_proxy(self, proxy: str):
        self.tool_proxy = proxy
        return self

    def get_tool_proxy(self):
        if self.tool_proxy:
            return self.tool_proxy
        elif self.parent:
            return self.parent.get_tool_proxy()
        else:
            return None

    def register(self, tool_name: str, desc: any, args: dict, func: callable, *, categories: (str, list) = None, require_proxy: bool=False):
        tool_info = {
            "tool_name": tool_name,
            "desc": desc,
            "args": args,
            "func": func,
            "require_proxy": require_proxy
        }
        if categories:
            if isinstance(categories, str):
                categories = [categories]
            tool_info.update({ "categories": categories })
            for category in categories:
                if category not in self.category_dict:
                    self.category_dict.update({ category: None })
        self.tool_runtime_ctx.update(tool_name, tool_info)
        return self

    def tool(self, tool_name: str):
        return RuntimeCtxNamespace(tool_name, self.tool_runtime_ctx)

    def get_tool_info(self, tool_name: str, *, with_args: bool=False, full: bool=False):
        full_info = self.tool(tool_name).get_trace_back()
        if full_info:
            if full:
                return full_info
            else:
                return {
                    "tool_name": full_info["tool_name"] if "tool_name" in full_info else tool_name,
                    "desc": full_info["desc"] if "desc" in full_info else "",
                    "args": full_info["args"] if "args" in full_info else {},
                } if with_args else {
                    "tool_name": full_info["tool_name"] if "tool_name" in full_info else tool_name,
                    "desc": full_info["desc"] if "desc" in full_info else "",
                }
        else:
            return None

    def get_tool_func(self, tool_name: str):
        full_info = self.tool(tool_name).get_trace_back()
        if full_info:
            if "func" in full_info and callable(full_info["func"]):
                return full_info["func"]
            else:
                return None
        else:
            return None

    def call_tool_func(self, tool_name: str, *args, **kwargs):
        func = self.get_tool_func(tool_name)
        if func:
            return func(*args, **kwargs)
        else:
            return None

    def get_tool_dict(self, *, categories: (str, list)=None, with_args=False):
        full_tool_dict = self.tool_runtime_ctx.get_trace_back()
        result = {}
        if categories:
            if isinstance(categories, str):
                categories = [categories]
            for tool_name, tool_info in full_tool_dict.items():
                if "categories" in tool_info:
                    for category in categories:
                        if category in tool_info["categories"]:
                            result.update({ tool_name: self.get_tool_info(tool_name, with_args=with_args) })
        else:
            for tool_name in full_tool_dict.keys():
                result.update({ tool_name: self.get_tool_info(tool_name, with_args=with_args) })
        return result

    def get_tool_list(self, *, categories: (str, list)=None, with_args=False):
        full_tool_dict = self.tool_runtime_ctx.get_trace_back()
        result = []
        if categories:
            if isinstance(categories, str):
                categories = [categories]
            for tool_name, tool_info in full_tool_dict.items():
                if "categories" in tool_info:
                    for category in categories:
                        if category in tool_info["categories"]:
                            result.append(self.get_tool_info(tool_name, with_args=with_args))
        else:
            for tool_name in full_tool_dict.keys():
                result.append(self.get_tool_info(tool_name, with_args=with_args))
        return result

    def set_category_desc(self, category: str, desc: any):
        self.category_dict.update({ category: desc })
        return self

    def get_category_dict(self):
        result = {}
        if self.parent:
            result = self.parent.get_category_dict()
        for key, value in self.category_dict.items():
            result.update({ key: value })
        return result