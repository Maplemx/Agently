import asyncio

async def repost_delta(delta_data, **kwargs):
    listener = kwargs["listener"]
    await listener.emit("delta", delta_data)

async def repost_delta_full(delta_data, **kwargs):
    listener = kwargs["listener"]
    await listener.emit("delta_full", delta_data)

async def repost_done(done_data, **kwargs):
    listener = kwargs["listener"]
    await listener.emit("done", done_data)

async def repost_done_full(done_data, **kwargs):
    listener = kwargs["listener"]
    await listener.emit("done_full", done_data)

async def register_response_suffix(runtime_ctx, **kwargs):
    listener = kwargs["listener"]
    delta_suffix = runtime_ctx.get("delta_suffix")
    delta_full_suffix = runtime_ctx.get("delta_full_suffix")
    done_suffix = runtime_ctx.get("done_suffix")
    done_full_suffix = runtime_ctx.get("done_full_suffix")
    if callable(delta_suffix):
        delta_suffix = [delta_suffix]
    if callable(delta_full_suffix):
        delta_full_suffix = [delta_full_suffix]
    if callable(done_suffix):
        done_suffix = [done_suffix]
    if callable(done_full_suffix):
        done_full_suffix = [done_full_suffix]
    for delta_suffix_func in delta_suffix:
        async def delta_suffix_func_with_kwargs(data):
            return await delta_suffix_func(data, **kwargs)
        listener.on("extract:delta", delta_suffix_func_with_kwargs)
    for delta_full_suffix_func in delta_full_suffix:
        async def delta_full_suffix_func_with_kwargs(data):
            return await delta_full_suffix_func(data, **kwargs)
        listener.on("extract:delta_full", delta_full_suffix_func_with_kwargs)
    for done_suffix_func in done_suffix:
        async def done_suffix_func_with_kwargs(data):
            return await done_suffix_func(data, **kwargs)
        listener.on("extract:done", done_suffix_func_with_kwargs)
    for done_full_suffix_func in done_full_suffix:
        async def done_full_suffix_func_with_kwargs(data):
            return await done_full_suffix_func(data, **kwargs)
        listener.on("extract:done_full", done_full_suffix_func_with_kwargs)
    reply_handler = runtime_ctx.get("reply_handler")
    if reply_handler:
        def update_final_reply(data):
            runtime_ctx.set("final_reply", reply_handler(data))
            return
        listener.on("done", update_final_reply)

    if runtime_ctx.get("is_debug"):
        listener.on("done_full", lambda data: print("[RESPONSE]\n", data))

def export(agently):
    agently\
        .manage_work_node("register_response_suffix")\
        .set_main_func(register_response_suffix)\
        .set_runtime_ctx({
            "delta_suffix": {
                "layer": "agent",
                "alias": {
                    "set": "set_delta_suffix",
                    "get": "get_delta_suffix",
                },
                "default": [repost_delta],
            },
            "delta_full_suffix": {
                "layer": "agent",
                "alias": {
                    "set": "set_delta_full_suffix",
                    "get": "get_delta_full_suffix",
                },
                "default": [repost_delta_full],
            },
            "done_suffix": {
                "layer": "agent",
                "alias": {
                    "set": "set_done_suffix",
                    "get": "get_done_suffix"
                },
                "default": [repost_done],
            },
            "done_full_suffix": {
                "layer": "agent",
                "alias": {
                    "set": "set_done_full_suffix",
                    "get": "get_done_full_suffix"
                },
                "default": [repost_done_full],
            },
            "reply_handler": {
                "layer": "request",
                "alias": { "set": "reply" },
            },
        })\
        .register()
    return