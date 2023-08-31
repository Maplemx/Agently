import asyncio
import json

def shorten_context(context_messages, context_length):
    short_context_messages = context_messages
    if len(json.dumps(short_context_messages)) <= context_length:
        return short_context_messages
    else:
        short_context_messages = short_context_messages[1:]
        return short_context_messages(short_context_messages, context_length)

def generate_context(runtime_ctx, **kwargs):
    session_runtime_ctx = kwargs["session_runtime_ctx"]
    full_context_messages = session_runtime_ctx.get("full_context_messages")
    if full_context_messages == None:
        session_runtime_ctx.set("full_context_messages", [])
        full_context_messages = []
    request_context_messages = session_runtime_ctx.get("request_context_messages")
    if request_context_messages == None:
        session_runtime_ctx.set("request_context_messages", [])
        request_context_messages = []
    extend_context_messages = runtime_ctx.get("extend_context_messages")
    context_length = runtime_ctx.get("context_length")
    if extend_context_messages:
        full_context_messages.extend(extend_context_messages)
        request_context_messages.extend(extend_context_messages)
    use_context = runtime_ctx.get("use_context")
    if use_context:
        request_context_messages = shorten_context(request_context_messages, context_length)
        session_runtime_ctx.set("request_context_messages", request_context_messages)
    else:
        session_runtime_ctx.set("request_context_messages", extend_context_messages)
    session_runtime_ctx.set("full_context_messages", full_context_messages)
    return

async def manage_context(runtime_ctx, **kwargs):
    session_runtime_ctx = kwargs["session_runtime_ctx"]

    generate_context(runtime_ctx, **kwargs)
    
    async def save_context_after_request(data):
        prompt_input = runtime_ctx.get("prompt_input")
        prompt_instruct = runtime_ctx.get("prompt_instruct")
        prompt_output = runtime_ctx.get("prompt_output")
        if prompt_input:
            request_content = str(prompt_input)
        elif prompt_output:
            request_content = str(prompt_output)
        else:
            request_content = str(rompt_instruct)
        final_reply = runtime_ctx.get("final_reply")
        new_context_messages = [
            { "role": "user", "content": str(request_content) },
            { "role": "assistant", "content": str(data) }
        ]
        session_runtime_ctx.extend("full_context_messages", new_context_messages)
        session_runtime_ctx.extend("request_context_messages", new_context_messages)

    listener = kwargs["listener"]
    listener.on("workflow_finish", save_context_after_request)

def export(agently):
    agently\
        .manage_work_node("manage_context")\
        .set_main_func(manage_context)\
        .set_runtime_ctx({
            "use_context": {
                "layer": "agent",
                "alias": { "set": "use_context" },
            },
            "extend_context_messages": {
                "layer": "request",
                "alias": {
                    "extend": "extend_context",
                },
                "default": [],
            },
            "context_length": {
                "layer": "agent",
                "alias": {
                    "set": "set_context_length",
                },
                "default": 3500,
            }
        })\
        .register()
    return