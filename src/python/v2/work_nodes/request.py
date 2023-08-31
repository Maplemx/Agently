import asyncio

from .request_process import update_process

async def request(runtime_ctx, **kwargs):
    process = kwargs["process"]
    request_method = runtime_ctx.get("request_method")
    if request_method not in process["request_main"]:
        request_method = "default"
    await process["request_main"][request_method](runtime_ctx, **kwargs)
    return

def export(agently):
    agently\
        .manage_work_node("request")\
        .set_main_func(request)\
        .set_runtime_ctx({
            "request_method": {
                "layer": "agent",
                "alias": { "set": "set_request_method" },
                "default": "default",
            },
        })\
        .register()
    update_process(agently.manage_work_node("request"))
    return