import asyncio
import json
import yaml
import re

async def handle_response_gpt(listener, loads_with_format_fix, runtime_ctx):
    buffer = {
        "message": { "role": "", "content": "" },
        "finish_reason": None
    }    
    
    async def handle_response_delta(delta_data):
        delta_content = delta_data["choices"][0]
        await listener.emit("delta_full_data", delta_content)
        if "delta" in delta_content and "content" in delta_content["delta"]:
            await listener.emit("delta", delta_content["delta"]["content"])
        if "delta" in delta_content and delta_content["delta"] != "":
            for key, value in delta_content["delta"].items():
                value = buffer["message"][key] + value if key in buffer["message"] else value
                buffer["message"].update({ key: value })
        if "finish_reason" in delta_content and delta_content["finish_reason"] != None:
            buffer["finish_reason"] = delta_content["finish_reason"]
        return

    listener.on("response_delta", handle_response_delta)

    async def handle_response_done(done_data):
        if done_data != None:
            await listener.emit("done_full_data", done_data["choices"][0])
            content = done_data["choices"][0]["message"]["content"]
            prompt_output_format = runtime_ctx.get("prompt_output_format")
            if prompt_output_format.upper() in ("JSON", "YAML"):
                content = loads_with_format_fix(content, prompt_output_format)
            await listener.emit("done", content)
        else:
            await listener.emit("done_full_data", buffer)
            await listener.emit("done", buffer["message"]["content"])

    listener.on("response_done", handle_response_done)

async def handle_response_minimax(listener, loads_with_format_fix, runtime_ctx):
    is_streaming = runtime_ctx.get("is_streaming")
    if is_streaming:

        async def handle_response_delta(delta_data):
            delta_content = delta_data["choices"][0]
            if "delta" in delta_content and delta_content["delta"] != "":
                await listener.emit("delta_full_data", { "delta": { "content": delta_content["delta"] }, "finish_reason": None })
                await listener.emit("delta", delta_content["delta"])
            if "finish_reason" in delta_content:
                await listener.emit("delta_full_data", { "delta": { "content": "", "finish_reason": delta_content["finish_reason"] } })

        listener.on("response_delta", handle_response_delta)
        await listener.emit("delta_full_data", { "delta": { "role": "assistant", "content": "" }, "finish_reason": None })

        async def handle_response_done(done_data):
            await listener.emit("done_full_data", {
                "index": done_data["choices"][0]["index"],
                "message": { "role": "assistant", "content": done_data["reply"] },
                "finish_reason": done_data["choices"][0]["finish_reason"],
            })
            content = done_data["reply"]
            prompt_output_format = runtime_ctx.get("prompt_output_format")
            if prompt_output_format.upper() in ("JSON", "YAML"):
                content = loads_with_format_fix(content, prompt_output_format)
            await listener.emit("done", content)

        listener.on("response_done", handle_response_done)
    else:
        async def handle_response_done(done_data):
            done_content = done_data["choices"][0]
            await listener.emit("done_full_data", {
                "index": done_content["index"],
                "message": { "role": "assistant", "content": done_content["text"] },
                "finish_reason": done_content["finish_reason"],
            })
            content = done_content["text"]
            prompt_output_format = runtime_ctx.get("prompt_output_format")
            if prompt_output_format.upper() in ("JSON", "YAML"):
                content = loads_with_format_fix(content, prompt_output_format)
            await listener.emit("done", content)

        listener.on("response_done", handle_response_done)

async def register_response_handlers(runtime_ctx, **kwargs):
    listener = kwargs["listener"]
    process = kwargs["process"]
    llm_name = runtime_ctx.get("llm_name")
    worker_agent = runtime_ctx.get("worker_agent")
    is_debug = runtime_ctx.get("is_debug")

    def loads_with_format_fix(content, output_format, fix_count = 0):
        fix_count += 1
        pattern = r"```(.*)\r?\n(.*)\r?\n```"
        re_pattern = re.compile(pattern, re.S)
        content = re_pattern.sub(r"\2", content)
        if worker_agent:
            def fix_yaml_format(content, e):
                if is_debug:
                    print('[Worker Agent Activated]')
                    print('Fix YAML Format Error:', e)
                    print('Current Ouput: ', content)
                    print('\n')
                content = worker_agent\
                    .input({
                        "origin YAML String": content,
                        "error": e,
                    })\
                    .output('Fixed YAML String only without explanation and decoration.')\
                    .start()
                if is_debug:
                    print('Fixed Content:', content)
                    print('\n')
                return content

            if fix_count >= 3:
                raise Exception(f'Format Error can not be fixed: [{ output_format }]\n{ content }')
            try:
                if output_format.upper() == "JSON":
                    content = json.loads(content)
                    return content
                elif output_format.upper() == "YAML":
                    content = yaml.safe_load(content)
                    prompt_output = runtime_ctx.get("prompt_output")
                    if len(content.keys()) < len(prompt_output.keys()):
                        if is_debug:
                            print('[Worker Agent Activated]')
                            print('Fix YAML Format Error: Not enough output keys.')
                            print('Output requirement: ', str(runtime_ctx.get("prompt_output")))
                            print('Current Output: ', content)
                            print('\n')
                        content = worker_agent\
                            .input({
                                "output keys requirement": str(runtime_ctx.get("prompt_output")),
                                "current output": content
                            })\
                            .output('Fixed YAML FORMAT STRING ONLY without explanation and decoration.')\
                            .start()
                        if is_debug:
                            print('Fixed Content:', content)
                            print('\n')
                        return loads_with_format_fix(content, output_format, fix_count)
                    else:
                        return content
            except json.JSONDecodeError as e:
                if is_debug:
                    print('[Worker Agent Activated]')
                    print('Fix JSON Format Error:', e.msg)
                    print('Current Ouput: ', content)
                    print('\n')
                content = worker_agent\
                    .input({
                        "origin JSON String": content,
                        "error": e.msg,
                        "position": e.pos,
                    })\
                    .output('Fixed JSON String only without explanation and decoration.')\
                    .start()
                if is_debug:
                    print('Fixed Content:', content)
                    print('\n')
                return loads_with_format_fix(content, output_format, fix_count)
            except yaml.scanner.ScannerError as e:
                content = fix_yaml_format(content, e)
                return loads_with_format_fix(content, output_format, fix_count)
            except yaml.parser.ParserError as e:
                content = fix_yaml_format(content, e)
                return loads_with_format_fix(content, output_format, fix_count)
        else:
            if output_format.upper() == "JSON":
                return json.loads(content)
            if output_format.upper() == "YAML":
                return yaml.safe_load(content)

    reply_handler = runtime_ctx.get("reply_handler")
    if reply_handler:
        def update_final_reply(data):
            runtime_ctx.set("final_reply", reply_handler(data))
            return
        listener.on("done", update_final_reply)

    await process["handle_response"][llm_name](listener, loads_with_format_fix, runtime_ctx)
    return

def export(agently):
    agently\
        .manage_work_node("register_response_handlers")\
        .set_main_func(register_response_handlers)\
        .set_process("handle_response", handle_response_gpt, "GPT")\
        .set_process("handle_response", handle_response_minimax, "MiniMax")\
        .set_runtime_ctx({
            "reply_handler": {
                "layer": "request",
                "alias": { "set": "reply" },
            }
        })\
        .register()
    return