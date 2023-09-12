import asyncio
import aiohttp
import json

from .loads_and_fix import loads_and_fix

'''
MiniMax
'''

def prepare_request_data(runtime_ctx):
    #default request_data
    request_data = {
        "llm_url": "https://api.minimax.chat/v1/text/chatcompletion",
        "data": {
            "model": "abab5.5-chat",
            "temperature": 1,
        },
    }
    #check auth info
    llm_auth = runtime_ctx.get("llm_auth")
    if "MiniMax" in llm_auth:
        request_data.update({ "llm_auth": llm_auth["MiniMax"] })
    else:
        raise Exception("[request]: llm_auth must be set to agent. use agent.set_llm_auth('MiniMax', { 'group_id': '...', 'api_key': '...' }) to set.")
    #update user customize settings
    cus_llm_url = runtime_ctx.get("llm_url")
    cus_llm_url = cus_llm_url["MiniMax"] if cus_llm_url and "MiniMax" in cus_llm_url else None
    if cus_llm_url:
        request_data.update({ "llm_url": cus_llm_url })
    request_data.update({ "proxy": runtime_ctx.get("proxy") })
    cus_request_options = runtime_ctx.get("request_options")
    cus_request_options = cus_request_options["MiniMax"] if cus_request_options and "MiniMax" in cus_request_options else None
    if isinstance(cus_request_options, dict):
        for options_name, options_value in cus_request_options.items():
            request_data["data"].update({ options_name: options_value })
    #get request messages
    request_messages = runtime_ctx.get("request_messages")
    #transform messages format
    prompt = ''
    minimax_user_name = runtime_ctx.get("minimax_user_name")
    minimax_bot_name = runtime_ctx.get("minimax_bot_name")
    final_request_messages = []
    for message in request_messages:
        if message["role"] == "system":
            prompt += f"{ message['content'] }\n"
        else:
            role_mapping = {
                "assistant": "BOT",
                "user": "USER",
            }
            final_request_messages.append({
                "sender_type": role_mapping[message["role"]],
                "text": message["content"]
            })
    request_data["data"].update({
        "messages": final_request_messages,
    })
    if prompt != '':
        request_data["data"].update({
            "prompt": prompt,
            "role_meta": {
                "user_name": minimax_user_name if minimax_user_name else "USER",
                "bot_name": minimax_bot_name if minimax_bot_name else "BOT",
            },
        })
    return request_data

async def request(request_data, listener):
    url = request_data["llm_url"] + "?GroupId=" + request_data["llm_auth"]["group_id"]
    data = request_data["data"].copy()
    data["stream"] = False
    headers = {
        "Authorization": f"Bearer { request_data['llm_auth']['api_key'] }",
        "Content-Type": "application/json",
    }
    proxy = request_data["proxy"] if "proxy" in request_data else {}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data, proxy=proxy) as response:
            response = await response.text()
            response = json.loads(response)
            if response["base_resp"]["status_code"] != 0:
                raise Exception(response["base_resp"])
            await listener.emit("response:done", response)
            return response

async def streaming(request_data, listener):
    url = request_data["llm_url"] + "?GroupId=" + request_data["llm_auth"]["group_id"]
    data = request_data["data"].copy()
    data["stream"] = True
    data["use_standard_sse"] = True
    headers = {
        "Authorization": f"Bearer { request_data['llm_auth']['api_key'] }",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    proxy = request_data["proxy"] if "proxy" in request_data else {}
    #response = requests.post(url, headers=headers, json=data, stream=True ,proxies=proxies)
    #return response
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data, proxy=proxy) as response:
            async for chunk in response.content.iter_chunks():
                if chunk[0]:
                    delta = json.loads(chunk[0].decode('utf-8')[6:][:-2])
                    if delta["reply"] == "":
                        await listener.emit("response:delta", delta)
                    else:
                        await listener.emit("response:done", delta)

async def handle_response(listener, runtime_ctx, worker_agent):
    is_streaming = runtime_ctx.get("is_streaming")

    if is_streaming:
        async def handle_response_delta(delta_data):
            delta_content = delta_data["choices"][0]
            if "extract:delta" in delta_content and delta_content["extract:delta"] != "":
                await listener.emit("extract:delta_full", { "extract:delta": { "content": delta_content["extract:delta"] }, "finish_reason": None })
                await listener.emit("extract:delta", delta_content["extract:delta"])
            if "finish_reason" in delta_content:
                await listener.emit("extract:delta_full", { "extract:delta": { "content": "", "finish_reason": delta_content["finish_reason"] } })

        listener.on("response:delta", handle_response_delta)
        await listener.emit("extract:delta_full", { "extract:delta": { "role": "assistant", "content": "" }, "finish_reason": None })

        async def handle_response_done(done_data):
            await listener.emit("extract:done_full", {
                "index": done_data["choices"][0]["index"],
                "message": { "role": "assistant", "content": done_data["reply"] },
                "finish_reason": done_data["choices"][0]["finish_reason"],
            })
            content = done_data["reply"]
            prompt_output_format = runtime_ctx.get("prompt_output_format")
            if prompt_output_format.upper() in ("JSON", "YAML"):
                content = await loads_and_fix(content, prompt_output_format, worker_agent=worker_agent, is_debug=runtime_ctx.get("is_debug"))
            await listener.emit("extract:done", content)

        listener.on("response:done", handle_response_done)
    else:
        async def handle_response_done(done_data):
            done_content = done_data["choices"][0]
            await listener.emit("extract:done_full", {
                "index": done_content["index"],
                "message": { "role": "assistant", "content": done_content["text"] },
                "finish_reason": done_content["finish_reason"],
            })
            content = done_content["text"]
            prompt_output_format = runtime_ctx.get("prompt_output_format")
            content = await loads_and_fix(content, prompt_output_format, worker_agent=worker_agent, is_debug=runtime_ctx.get("is_debug"))
            await listener.emit("extract:done", content)

        listener.on("response:done", handle_response_done)