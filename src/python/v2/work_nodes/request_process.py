# -- coding: utf8 --
import asyncio
import aiohttp
import json

'''
Main
'''
async def request_main_default(runtime_ctx, **kwargs):
    process = kwargs["process"]
    listener = kwargs["listener"]
    llm_name = runtime_ctx.get("llm_name")

    request_data = process["prepare_request_data"][llm_name](runtime_ctx)

    if runtime_ctx.get("is_debug"):
        print("[REQUEST]")
        print(request_data["data"]["messages"])

    is_streaming = runtime_ctx.get("is_streaming")
        
    if not is_streaming:
        response = await process["request_llm"][llm_name](request_data, listener)
        if runtime_ctx.get("is_debug"):
            print("[RESPONSE]")
            print(response)
    else:
        response = await process["streaming_llm"][llm_name](request_data, listener)
    return


'''
OpenAI GPT
'''
def prepare_request_data_gpt(runtime_ctx):
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
        raise Exception(f"[request]: llm_auth must be set to agent. use agent.set_llm_auth('GPT', <Your-API-Auth>) to set.")
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

async def request_gpt(request_data, listener):
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
            await listener.emit("response_done", response)
            return response

async def streaming_gpt(request_data, listener):
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
                        await listener.emit("response_delta", json.loads(delta))
                    else:
                        await listener.emit("response_done", None)

'''
MiniMax
'''
def prepare_request_data_minimax(runtime_ctx):
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
        raise Exception("[request]: llm_auth must be set to agent. use agent.set_llm_auth('MiniMax', <Your-API-Auth>) to set.")
    #update user customize settings
    cus_llm_url = runtime_ctx.get("llm_url")
    cus_llm_url = cus_llm_url["MiniMax"] if cus_llm_url and "MiniMax" in cus_llm_url else None
    if cus_llm_url:
        request_data.update({ "llm_url": cus_llm_url["MiniMax"] })
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

async def request_minimax(request_data, listener):
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
            await listener.emit("response_done", response)
            return response

async def streaming_minimax(request_data, listener):
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
                        await listener.emit("response_delta", delta)
                    else:
                        await listener.emit("response_done", delta)

def update_process(work_node_management):
    result = work_node_management\
        .set_process("request_main", request_main_default, "default")\
        .set_process("prepare_request_data", prepare_request_data_gpt, "GPT")\
        .set_process("request_llm", request_gpt, "GPT")\
        .set_process("streaming_llm", streaming_gpt, "GPT")\
        .set_process("prepare_request_data", prepare_request_data_minimax, "MiniMax")\
        .set_process("request_llm", request_minimax, "MiniMax")\
        .set_process("streaming_llm", streaming_minimax, "MiniMax")\
        .set_runtime_ctx({
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
            "proxy": {
                "layer": "agent",
                "alias": { "set": "set_proxy" },
            },
            "is_streaming": {
                "layer": "session",
                "alias": { "set": "set_streaming" },
                "default": False,
            },
            "request_options": {
                "layer": "session",
                "alias": { "set_kv": "set_request_options" },
            },
            "minimax_bot_name": {
                "layer": "agent",
                "alias": { "set": "set_minimax_bot_name" },
            },
            "minimax_user_name": {
                "layer": "agent",
                "alias": { "set": "set_minimax_user_name" },
            },
        })\
        .update()
    return