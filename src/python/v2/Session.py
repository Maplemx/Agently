import asyncio
import concurrent.futures

from .RuntimeCtx import RuntimeCtx
from .runtime_ctx_settings import inject_alias, set_default_runtime_ctx

class Listener(object):
    def __init__(self):
        self.handlers = {}
        return

    def on(self, event, handler):
        if event not in self.handlers:
            self.handlers[event] = []
        self.handlers[event].append(handler)
        return self

    async def emit(self, event, *args, **kwargs):
        if event in self.handlers:
            for handler in self.handlers[event]:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args, **kwargs)
                else:
                    handler(*args, **kwargs)

class Session(object):
    def __init__(self, agent):
        self.agent_runtime_ctx = agent.runtime_ctx
        self.runtime_ctx = RuntimeCtx(agent.runtime_ctx)
        self.workflows = agent.workflows
        self.work_nodes = agent.work_nodes
        inject_alias(self, "agent")
        inject_alias(self, "session")
        inject_alias(self, "request")
        set_default_runtime_ctx(self.runtime_ctx, "session")
        self.request_runtime_ctx = RuntimeCtx(self.runtime_ctx)        
        set_default_runtime_ctx(self.request_runtime_ctx, "request")

        self.is_working = False
        self.listener = Listener()
        self.final_result = None
        return

    def set(self, key, value, **kwargs):
        target_runtime_ctx = kwargs.get("target_runtime_ctx", "session")
        if target_runtime_ctx == "request":
            self.request_runtime_ctx.set(key, value, **kwargs)
        else:
            self.runtime_ctx.set(key, value, **kwargs)
        return self

    def get(self, key, **kwargs):
        target_runtime_ctx = kwargs.get("target_runtime_ctx", "session")
        if target_runtime_ctx == "request":
            self.request_runtime_ctx.get(key, **kwargs)
        else:
            self.runtime_ctx.get(key, **kwargs)
        return self

    def append(self, key, value, **kwargs):
        target_runtime_ctx = kwargs.get("target_runtime_ctx", "session")
        if target_runtime_ctx == "request":
            self.request_runtime_ctx.append(key, value, **kwargs)
        else:
            self.runtime_ctx.append(key, value, **kwargs)  
        return self

    def extend(self, key, value, **kwargs):
        target_runtime_ctx = kwargs.get("target_runtime_ctx", "session")
        if target_runtime_ctx == "request":
            self.request_runtime_ctx.extend(key, value, **kwargs)
        else:
            self.runtime_ctx.extend(key, value, **kwargs)
        return self

    def on(self, event, handler):
        self.listener.on(event, handler)
        return self

    async def __start(self, workflow_name):
        if self.is_working:
            await asyncio.sleep(0.1)
            await self.__start(workflow_name)
        else:
            self.is_working = True
            workflow = self.workflows.get(workflow_name)
            if workflow:
                if not isinstance(workflow, list) or len(workflow) == 0:
                    raise Exception(f"[session start]: No work node in workflow { workflow_name }")

                self.final_result = None

                async def set_final_result(data):
                    self.final_result = data
                    return

                self.listener.on('done', set_final_result)

                async def reset(data):
                    self.request_runtime_ctx = None
                    self.request_runtime_ctx = RuntimeCtx(self.runtime_ctx) 
                    set_default_runtime_ctx(self.request_runtime_ctx, "request")
                    self.listener = None
                    self.listener = Listener()
                    self.is_working = False
                    return

                self.listener.on('workflow_finish', reset)

                for work_node_name in workflow:
                    work_node = self.work_nodes.get(work_node_name)
                    if asyncio.iscoroutinefunction(work_node["main"]):
                        await work_node["main"](\
                            self.request_runtime_ctx,\
                            listener = self.listener,\
                            process = work_node["process"],\
                            session_runtime_ctx = self.runtime_ctx,\
                            agent_runtime_ctx = self.agent_runtime_ctx,\
                            worker_agent = self.runtime_ctx.get("worker_agent")\
                        )
                    else:
                        work_node["main"](\
                            self.request_runtime_ctx,\
                            listener = self.listener,\
                            process = work_node["process"],\
                            session_runtime_ctx = self.runtime_ctx,\
                            agent_runtime_ctx = self.agent_runtime_ctx,\
                            worker_agent = self.runtime_ctx.get("worker_agent")\
                        )
                runtime_ctx_final_reply = self.request_runtime_ctx.get("final_reply")
                result = runtime_ctx_final_reply if runtime_ctx_final_reply else self.final_result
                await self.listener.emit('workflow_finish', result)
                return result
            else:
                raise Exception(f'[session start]: No workflow named { workflow_name }')

    def start(self, workflow_name="default"):
        old_loop = asyncio.get_event_loop()
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, self.__start(workflow_name=workflow_name))
            result = future.result()
        new_loop.stop()
        asyncio.set_event_loop(old_loop)
        return result