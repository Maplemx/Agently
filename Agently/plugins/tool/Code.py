from .utils import ToolABC

class Code(ToolABC):
    def __init__(self, tool_manager: object):
        self.tool_manager = tool_manager

    def calculate(self, code: str, result_vars: list=None):
        results = {
            "origin": None,
            "for_agent": None,
        }
        global_vars = self.tool_manager.runtime_cache.get("global_vars", {})
        local_vars = self.tool_manager.runtime_cache.get("local_vars", {})
        exec(code, global_vars, local_vars)
        self.tool_manager.runtime_cache.update({ "global_vars": global_vars })
        self.tool_manager.runtime_cache.update({ "local_vars": local_vars })
        result = {}
        if result_vars:
            for result_var in result_vars:
                result.update({ result_var["why"]: local_vars.get(result_var["var_name"]) })
            results = {
                "origin": result,
                "for_agent": result,
            }
        else:
            results = {
                "origin": local_vars,
                "for_agent": local_vars,
            }
        return results

    def export(self):
        return {
            "calculate": {
                "desc": "execute Python code to storage result to variables",
                "args": {
                    "code": ("Python Code assigning values to variables", "[*Required]"),
                    "result_vars": [{
                        "var_name": ("String", "[*Required]var name in {code}"),
                        "why": ("String", "[*Required]brief purpose to get result of {var_name}")
                    }],
                },
                "func": self.calculate,
            },
        }

def export():
    return ("Code", Code)