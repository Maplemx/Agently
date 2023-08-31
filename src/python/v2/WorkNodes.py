from .RuntimeCtx import RuntimeCtx

class WorkNodeManagement(object):
    def __init__(self, work_nodes, work_node_name):
        self.work_node_name = work_node_name
        self.runtime_ctx = RuntimeCtx()
        self.work_nodes = work_nodes
        self.__init_runtime_ctx()
        return

    def __init_runtime_ctx(self):
        self.runtime_ctx.set("main", None)
        self.runtime_ctx.set("process", {})
        self.runtime_ctx.set("runtime_ctx_settings", {})
        self.runtime_ctx.set("error_list", [])
        self.runtime_ctx.set("warning_list", [])
        return

    def set_main_func(self, main_func):
        if not callable(main_func):
            self.runtime_ctx.append("error_list", "[set_main_func]: main_func must be a callable function.")
        else:
            self.runtime_ctx.set("main", main_func)            
        return self

    def set_process(self, process_name, process_func, process_condition = "default"):
        if not isinstance(process_name, str):
            self.runtime_ctx.append("error_list", "[set_process]: process_name must be a string.")
        elif not callable(process_func):
            self.runtime_ctx.append("error_list", "[set_process]: process_func must be a callable function.")
        else:
            process_runtime_ctx = self.runtime_ctx.get("process")
            if process_name not in process_runtime_ctx:
                process_runtime_ctx.update({ process_name: {} })
            process_runtime_ctx[process_name].update({ process_condition: process_func })
            self.runtime_ctx.set("process", process_runtime_ctx)
        return self

    def set_runtime_ctx(self, runtime_ctx_settings_dict):
        self.runtime_ctx.update("runtime_ctx_settings", runtime_ctx_settings_dict)
        return self

    def __check(self, data):
        if data["main"] == None:
            self.runtime_ctx.append("error_list", "[register]: No main func is set. Use .set_main_func(main_func) to set.")
        if len(data["process"]) == 0:
            self.runtime_ctx.append("warning_list", "[register]: No process is set. Use .set_process(process_name, process_func, <process_condition>) to set if needed.")
        if len(data["runtime_ctx_settings"]) == 0:
            self.runtime_ctx.append("warning_list", "[register]: No runtime_ctx_settings is set. Use .set_runtime_ctx(runtime_ctx_settings_dict) to set if needed.")
        return 

    def register(self):
        runtime_ctx_data = {
            "main": self.runtime_ctx.get("main"),
            "process": self.runtime_ctx.get("process"),
            "runtime_ctx_settings": self.runtime_ctx.get("runtime_ctx_settings"),
        }

        self.__check(runtime_ctx_data)
        if self.work_nodes.get(self.work_node_name) != None:
            self.runtime_ctx.append("error_list", f"[register]: Work node '{ self.work_node_name }' existed.")

        error_list = self.runtime_ctx.get("error_list")
        warning_list = self.runtime_ctx.get("warning_list")

        if len(error_list) == 0:
            self.work_nodes.set(\
                self.work_node_name,\
                runtime_ctx_data\
            )
            self.__init_runtime_ctx()
            return {
                "ok": True,
                "message": {
                    "error": error_list,
                    "warning": warning_list
                }
            }
        else:
            self.__init_runtime_ctx()
            raise Exception({
                "ok": False,
                "message": {
                    "error": error_list,
                    "warning": warning_list,
                },
            })

    def __update_dict(self, target, dict_item):
        for key in dict_item.keys():
            if key not in target:
                target[key] = {}
            if isinstance(dict_item[key], dict):
                self.__update_dict(target[key], dict_item[key])
            else:
                if dict_item[key] != None:
                    target[key] = dict_item[key]

    def update(self):
        work_node = self.work_nodes.get(self.work_node_name)

        if work_node == None:
            raise Exception({
                "ok": False,
                "message": {
                    "error": [f"[update]: Work node '{ self.work_node_name }' is not existed."],
                    "warning": [],
                },
            })

        update_work_node_dict = {
            "main": self.runtime_ctx.get("main"),
            "process": self.runtime_ctx.get("process"),
            "runtime_ctx_settings": self.runtime_ctx.get("runtime_ctx_settings"),
        }

        self.__update_dict(work_node, update_work_node_dict)

        self.__check(work_node)

        error_list = self.runtime_ctx.get("error_list")
        warning_list = self.runtime_ctx.get("warning_list")

        if len(error_list) == 0:
            self.work_nodes.set(\
                self.work_node_name,\
                work_node\
            )
            self.__init_runtime_ctx()
            return {
                "ok": True,
                "message": {
                    "error": error_list,
                    "warning": warning_list
                }
            }
        else:
            self.__init_runtime_ctx()
            raise Exception({
                "ok": False,
                "message": {
                    "error": error_list,
                    "warning": warning_list,
                },
            })


class WorkNodes(object):
    def __init__(self, runtime_ctx):
        self.runtime_ctx = runtime_ctx
        return

    def manage_work_node(self, work_node_name):
        return WorkNodeManagement(self, work_node_name)

    def set(self, work_node_name, work_node):
        self.runtime_ctx.set(work_node_name, work_node, domain = "work_nodes")
        return

    def update(self, work_node_name, update_work_node_dict):
        self.runtime_ctx.update(work_node_name, update_work_node_dict, domain = "work_nodes")
        return

    def get(self, work_node_name):
        return self.runtime_ctx.get(work_node_name, domain = "work_nodes")