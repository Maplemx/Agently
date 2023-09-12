import asyncio
import aiohttp
import json

from .loads_and_fix import loads_and_fix

'''
OpenAI GPT
'''

def prepare_request_data(runtime_ctx):
    #default request_data
    request_data = {
        "llm_url": "https://api.openai.com/v1/chat/completions",
        "data": {
            "model": "gpt-3.5-turbo",
            "temperature": 1,
        },
    }
    #check auth info
    llm_auth = runtime_ctx.get("llm_auth")
    if "GPT" in llm_auth:
        request_data.update({ "llm_auth": llm_auth["GPT"] })
    else:
        raise Exception(f"[request]: llm_auth must be set to agent. use agent.set_llm_auth('GPT', <Your-API-Key>) to set.")
    #update user customize settings
    cus_llm_url = runtime_ctx.get("llm_url")
    cus_llm_url = cus_llm_url["GPT"] if cus_llm_url and "GPT" in cus_llm_url else None
    if cus_llm_url:
        request_data.update({ "llm_url": cus_llm_url })
    request_data.update({ "proxy": runtime_ctx.get("proxy") })
    cus_request_options = runtime_ctx.get("request_options")
    cus_request_options = cus_request_options["GPT"] if cus_request_options and "GPT" in cus_request_options else None
    if isinstance(cus_request_options, dict):
        for options_name, options_value in cus_request_options.items():
            request_data["data"].update({ options_name: options_value })
    #get request messages, no transform because standard message style follow GPT API style
    request_data["data"].update({ "messages": runtime_ctx.get("request_messages") })
    return request_data

async def request(request_data, listener):
    url = request_data["llm_url"]
    data = request_data["data"].copy()
    data["stream"] = False
    headers = {
        "Authorization": f"Bearer { request_data['llm_auth'] }",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    proxy = request_data["proxy"] if "proxy" in request_data else {}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data, proxy=proxy) as response:
            response = await response.json()
            await listener.emit("response:done", response)
            return response

async def streaming(request_data, listener):
    url = request_data["llm_url"]
    data = request_data["data"].copy()
    data["stream"] = True
    headers = {
        "Authorization": f"Bearer { request_data['llm_auth'] }",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    proxy = request_data["proxy"] if "proxy" in request_data else {}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data, proxy=proxy) as response:
            async for chunk in response.content.iter_chunks():
                if chunk[0]:
                    delta = chunk[0].decode('utf-8')[6:][:-2]
                    if delta != '[DONE]':
                        await listener.emit("response:delta", json.loads(delta))
                    else:
                        await listener.emit("response:done", None)

async def handle_response(listener, runtime_ctx, worker_agent):
    buffer = {
        "message": { "role": "", "content": "" },
        "finish_reason": None
    }    
    
    async def handle_response_delta(delta_data):
        delta_content = delta_data["choices"][0]
        await listener.emit("extract:delta_full", delta_content)
        if "delta" in delta_content and "content" in delta_content["delta"]:
            await listener.emit("extract:delta", delta_content["delta"]["content"])
        if "delta" in delta_content and delta_content["delta"] != "":
            for key, value in delta_content["delta"].items():
                value = buffer["message"][key] + value if key in buffer["message"] else value
                buffer["message"].update({ key: value })
        if "finish_reason" in delta_content and delta_content["finish_reason"] != None:
            buffer["finish_reason"] = delta_content["finish_reason"]
        return

    listener.on("response:delta", handle_response_delta)

    async def handle_response_done(done_data):
        if done_data != None:
            await listener.emit("extract:done_full", done_data["choices"][0])
            content = done_data["choices"][0]["message"]["content"]
            prompt_output_format = runtime_ctx.get("prompt_output_format")
            content = await loads_and_fix(content, prompt_output_format, worker_agent=worker_agent, is_debug=runtime_ctx.get("is_debug"))
            await listener.emit("extract:done", content)
        else:
            await listener.emit("extract:done_full", buffer)
            await listener.emit("extract:done", buffer["message"]["content"])

    listener.on("response:done", handle_response_done)