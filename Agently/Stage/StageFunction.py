class StageFunction:
    def __init__(self, stage, func, *args, **kwargs):
        self._stage = stage
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._on_success_handler = None
        self._on_error_handler = None
    
    def set(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        return self
    
    def args(self, *args):
        self._args = args
        return self
    
    def kwargs(self, **kwargs):
        self._kwargs = kwargs
        return self
    
    def on_success(self, on_success_handler):
        self._on_success_handler = on_success_handler
        return self

    def on_error(self, on_error_handler):
        self._on_error_handler = on_error_handler
        return self

    def go(self):
        return self._stage.go(
            self._func,
            *self._args,
            on_success=self._on_success_handler,
            on_error=self._on_error_handler,
            **self._kwargs
        )
    
    def get(self):
        return self._stage.get(
            self._func,
            *self._args,
            on_success=self._on_success_handler,
            on_error=self._on_error_handler,
            **self._kwargs
        )

class StageFunctionMixin:        
    def func(self, func):
        return StageFunction(self, func)