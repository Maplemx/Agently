import inspect
import ast
from .utils import ComponentABC

class Decorator(ComponentABC):
    def __init__(self, agent: object):
        self.agent = agent

    def auto_func(self, func: callable):
        def wrapper(*args, **kwargs):
            # generate input dict
            signature = inspect.signature(func)
            arguments = signature.bind(*args, **kwargs)
            arguments.apply_defaults()
            input_dict = {}
            for param in signature.parameters:
                input_dict.update({ param: arguments.arguments[param] })
            # generate instruction
            instruction = inspect.getdoc(func)
            # generate output dict
            output_dict = signature.return_annotation
            return (
                self.agent
                    .input(input_dict)
                    .instruct(instruction)
                    .output(output_dict)
                    .start()
            )
        return wrapper

    def on_event(self, event: str, *, is_await:bool=False):
        if not event.startswith("response:") and not event.startswith("tool:"):
            event = "response:" + event
        def decorator(func: callable):
            self.agent.add_event_listener(event, func, is_await=is_await)
        return decorator

    def register_tool(self, **tool_info_kwrags):
        def decorator(func: callable):
            # get tool name
            if "tool_name" not in tool_info_kwrags:
                tool_info_kwrags.update({ "tool_name": func.__name__ })
            # get desc
            if "desc" not in tool_info_kwrags:
                tool_info_kwrags.update({ "desc": inspect.getdoc(func) })
            # get args
            if "args" not in tool_info_kwrags:
                func_ast = ast.parse(inspect.getsource(func))
                tool_info_kwrags.update({ "args": {} })
                for node in func_ast.body[0].args.args:
                    if node.arg != "self":
                        tool_info_kwrags["args"].update({
                            node.arg:
                                (node.annotation.dims[0].value, node.annotation.dims[1].value)
                                if isinstance(node.annotation, ast.Tuple)
                                else (type(node.annotation.value).__name__, node.annotation.value)
                        })
            # get func
            tool_info_kwrags.update({ "func": func })
            self.agent.register_tool(**tool_info_kwrags)
            return func
        return decorator

        
    def export(self):
        return {
            "prefix": None,
            "suffix": None,
            "alias": {
                "auto_func": { "func": self.auto_func, "return_value": True },
                "on_event": { "func": self.on_event, "return_value": True },
                "tool": { "func": self.register_tool, "return_value": True },
            },
        }

def export():
    return ("Decorator", Decorator)