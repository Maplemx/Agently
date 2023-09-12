import asyncio

from .request_process import update_process

'''
Main
'''
async def request_main_default(runtime_ctx, **kwargs):
    process = kwargs["process"]
    listener = kwargs["listener"]
    worker_agent = runtime_ctx.get("worker_agent")
    llm_name = runtime_ctx.get("llm_name")

    #prepare request data
    request_data = process["prepare_request_data"][llm_name](runtime_ctx)

    if runtime_ctx.get("is_debug"):
        print("[REQUEST]")
        print(request_data["data"]["messages"])

    is_streaming = runtime_ctx.get("is_streaming")

    #register all handlers
    await process["handle_response"][llm_name](listener, runtime_ctx, worker_agent)
    
    #then start request    
    if not is_streaming:
        response = await process["request_llm"][llm_name](request_data, listener)
    else:
        response = await process["streaming_llm"][llm_name](request_data, listener)
    return

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
        .set_process("request_main", request_main_default, "default")\
        .set_runtime_ctx({
            "request_method": {
                "layer": "agent",
                "alias": { "set": "set_request_method" },
                "default": "default",
            },
            "llm_name": {
                "layer": "agent",
                "alias": { "set": "set_llm_name" },
                "default": "GPT"
            },
            "llm_url": {
                "layer": "agent",
                "alias": { "set_kv": "set_llm_url" },
            },
            "llm_auth": {
                "layer": "agent",
                "alias": { "set_kv": "set_llm_auth" },
            },
            "request_options": {
                "layer": "agent",
                "alias": { "set_kv": "set_request_options" },
            },
            "proxy": {
                "layer": "agent",
                "alias": { "set": "set_proxy" },
            },
            "is_streaming": {
                "layer": "session",
                "alias": { "set": "set_streaming" },
                "default": False,
            },
        })\
        .register()
    update_process(agently.manage_work_node("request"))
    return