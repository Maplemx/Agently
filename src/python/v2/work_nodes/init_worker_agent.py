import asyncio
async def init_worker_agent(runtime_ctx, **kwargs):
    worker_agent = kwargs["worker_agent"]
    if worker_agent != None:
        llm_name = runtime_ctx.get("llm_name")
        llm_url = runtime_ctx.get("llm_url")
        llm_auth = runtime_ctx.get("llm_auth")
        proxy = runtime_ctx.get("proxy")
        request_options = runtime_ctx.get("request_options")

        # GPT first
        if "GPT" in llm_auth and llm_auth["GPT"] != None:
            worker_agent.set_llm_name("GPT")
            if llm_url and "GPT" in llm_url:
                worker_agent.set_llm_url("GPT", llm_url["GPT"])
            worker_agent.set_llm_auth("GPT", llm_auth["GPT"])
            if proxy:
                worker_agent.set_proxy(runtime_ctx.get("proxy"))
            if request_options and "GPT" in request_options:
                worker_agent.set_request_options("GPT", request_options["GPT"])
        # No GPT then use user current llm
        else:
            worker_agent.set_llm_name(llm_name)
            if llm_url and llm_name in llm_url:
                worker_agent.set_llm_url(llm_name, llm_url[llm_name])
            if llm_auth and llm_name in llm_auth:
                worker_agent.set_llm_auth(llm_name, llm_auth[llm_name])
            if proxy:
                worker_agent.set_proxy(runtime_ctx.get("proxy"))
            if request_options and llm_name in request_options:
                worker_agent.set_request_options(llm_name, request_options[llm_name])
    return

def export(agently):
    agently\
        .manage_work_node("init_worker_agent")\
        .set_main_func(init_worker_agent)\
        .register()
    return