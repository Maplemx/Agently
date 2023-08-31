from .RuntimeCtx import RuntimeCtx

class Workflows(object):
    def __init__(self, runtime_ctx):
        self.runtime_ctx = runtime_ctx
        return

    def set(self, workflow_name, workflow):
        error_list = []
        if not isinstance(workflow_name, str):
            error_list.append("[set_workflow]: workflow_name must be a string.")
        if not isinstance(workflow, list):
            error_list.append("[set_workflow]: workflow must be a list.")
        if len(error_list) > 0:
            return {
                "ok": False,
                "message": {
                    "error": error_list,
                },
            }
        work_nodes = self.runtime_ctx.get_all_above(domain = "work_nodes")
        for work_node_name in workflow:
            if work_node_name not in work_nodes:
                error_list.append(f"[set_workflow]: '{ work_node_name }' is not in work_nodes dict.")
        if len(error_list) > 0:
            return {
                "ok": False,
                "message": {
                    "error": error_list,
                },
            }
        self.runtime_ctx.set(workflow_name, workflow, domain = "workflows")
        return { "ok": True }

    def get(self, workflow_name):
        return self.runtime_ctx.get(workflow_name, domain = "workflows")