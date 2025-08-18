import inspect

from typing import Callable

from agently.core import BaseAgent


class AutoFuncExtension(BaseAgent):
    def auto_func(self, func: Callable):
        if inspect.iscoroutinefunction(func):

            async def async_wrapper(*args, **kwargs):
                signature = inspect.signature(func)
                arguments = signature.bind(*args, **kwargs)
                arguments.apply_defaults()
                input_dict = {}
                for param in signature.parameters:
                    input_dict.update({param: arguments.arguments[param]})
                # generate instruction
                instruction = inspect.getdoc(func)
                # generate output dict
                output_dict = signature.return_annotation
                return await self.input(input_dict).instruct(instruction).output(output_dict).async_start()

            return async_wrapper
        elif (
            inspect.isfunction(func) and not inspect.isasyncgenfunction(func) and not inspect.isgeneratorfunction(func)
        ):

            def wrapper(*args, **kwargs):
                signature = inspect.signature(func)
                arguments = signature.bind(*args, **kwargs)
                arguments.apply_defaults()
                input_dict = {}
                for param in signature.parameters:
                    input_dict.update({param: arguments.arguments[param]})
                # generate instruction
                instruction = inspect.getdoc(func)
                # generate output dict
                output_dict = signature.return_annotation
                return self.input(input_dict).instruct(instruction).output(output_dict).start()

            return wrapper
        else:
            raise TypeError(f"Error: Cannot decorate generator as an automatic function.\nFunction: { func }")
