def assemble_request_messages(runtime_ctx, **kwargs):
    session_runtime_ctx = kwargs["session_runtime_ctx"]

    request_system_message = runtime_ctx.get("request_system_message")
    request_context_messages = session_runtime_ctx.get("request_context_messages")
    request_prompt_message = runtime_ctx.get("request_prompt_message")
    request_messages = []
    if request_system_message:
        request_messages.append(request_system_message)
    if request_context_messages:
        request_messages.extend(request_context_messages)
    request_messages.append(request_prompt_message)
    runtime_ctx.set("request_messages", request_messages)

def export(agently):
    agently\
        .manage_work_node("assemble_request_messages")\
        .set_main_func(assemble_request_messages)\
        .set_runtime_ctx({
            "request_messages": { "default": [], "layer": "request" }
        })\
        .register()
    return