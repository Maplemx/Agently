import copy

from .runtime_ctx_settings import inject_alias, set_default_runtime_ctx
from .RuntimeCtx import RuntimeCtx
from .Session import Session

class Agent(object):
    def __init__(self, agently, blueprint = None):
        if blueprint:
            self.runtime_ctx = copy.deepcopy(blueprint.runtime_ctx)
            self.workflows = copy.deepcopy(blueprint.workflows)
            self.work_nodes = copy.deepcopy(blueprint.work_nodes)
        else:
            self.runtime_ctx = RuntimeCtx(agently.runtime_ctx)
            self.workflows = agently.workflows
            self.work_nodes = agently.work_nodes
        inject_alias(self, "agent")
        set_default_runtime_ctx(self.runtime_ctx, "agent")
        return
    '''
    Basic RuntimeCtx Management
    '''
    def set(self, key, value, **kwargs):
        self.runtime_ctx.set(key, value, **kwargs)
        return self

    def get(self, key, **kwargs):
        self.runtime_ctx.get(key, **kwargs)
        return self

    def append(self, key, value, **kwargs):
        self.runtime_ctx.append(key, value, **kwargs)
        return self

    def extend(self, key, value, **kwargs):
        self.runtime_ctx.extend(key, value, **kwargs)
        return self
    '''
    Create Session
    '''
    def create_session(self):
        return Session(self)