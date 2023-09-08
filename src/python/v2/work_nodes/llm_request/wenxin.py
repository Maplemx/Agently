import asyncio
import aiohttp
import json

from .loads_and_fix import loads_and_fix

#百度千帆大模型平台限时免费模型列表可查阅：
#https://cloud.baidu.com/doc/WENXINWORKSHOP/s/2lktec9ey

#获取千帆access_token，可复制下面的方法运行，有效期30天，过期后需要重新运行
'''
async def get_wx_access_token (api_key, secret_key):
    url = "https://aip.baidubce.com/oauth/2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": api_key,
        "client_secret": secret_key,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(\
            url,\
            data=data,\
        ) as response:
            response = await response.json()
            return response
result = asyncio.run(get_wx_access_token("Your-API-Key", "Your-Secret-Key"))
print(result["access_token"])
'''

'''
Baidu WenXin Workshop
'''

def prepare_request_data(runtime_ctx):
    wx_model_type = runtime_ctx.get("wx_model_type")
    wx_model_name = runtime_ctx.get("wx_model_name")
    #default request_data
    request_data = {
        "llm_url": f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/{ wx_model_type }/{ wx_model_name }",
        "data": {},
    }
    #check auth info
    llm_auth = runtime_ctx.get("llm_auth")
    if "wenxin" in llm_auth:
        request_data.update({ "llm_auth": llm_auth["wenxin"] })
    else:
        raise Exception(f"[request]: llm_auth must be set to agent. use agent.set_llm_auth('wenxin', <Your-access-token>) to set.\nHow to generate access token: https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Sllyztytp")
    #update user customize settings
    cus_llm_url = runtime_ctx.get("llm_url")
    cus_llm_url = cus_llm_url["wenxin"] if cus_llm_url and "wenxin" in cus_llm_url else None
    if cus_llm_url:
        request_data.update({ "llm_url": cus_llm_url })
    request_data.update({ "proxy": runtime_ctx.get("proxy") })
    cus_request_options = runtime_ctx.get("request_options")
    cus_request_options = cus_request_options["wenxin"] if cus_request_options and "wenxin" in cus_request_options else None
    if isinstance(cus_request_options, dict):
        for options_name, options_value in cus_request_options.items():
            request_data["data"].update({ options_name: options_value })
    #get request messages
    request_messages = runtime_ctx.get("request_messages")
    #transform messages format
    for message in request_messages:
        if message["role"] == "system":
            message["role"] = "user"
    request_data["data"].update({ "messages": request_messages })
    #prepare prompt for completions
    if wx_model_type == "completions":
        prompt = ""
        for message in request_messages:
            prompt += message["content"] + '\n'
        request_data["prompt"] = prompt
    return request_data

async def request(request_data, listener):
    url = request_data["llm_url"] + '?access_token=' + request_data["llm_auth"]
    data = request_data["data"].copy()
    if "prompt" in request_data:
        del data["messages"]
        data["prompt"] = request_data["prompt"]
    data["stream"] = False
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    proxy = request_data["proxy"] if "proxy" in request_data else {}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data, proxy=proxy) as response:
            response = await response.json()
            await listener.emit("response_done", response)
            return response

async def streaming(request_data, listener):
    url = request_data["llm_url"] + '?access_token=' + request_data["llm_auth"]
    data = request_data["data"].copy()
    if "prompt" in request_data:
        del data["messages"]
        data["prompt"] = request_data["prompt"]
    data["stream"] = True
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    proxy = request_data["proxy"] if "proxy" in request_data else {}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data, proxy=proxy) as response:
            async for chunk in response.content.iter_chunks():
                if chunk[0]:
                    try:
                        delta = chunk[0].decode('utf-8')[6:][:-2]
                        delta = json.loads(delta)
                        await listener.emit("response_delta", delta)
                        if delta["is_end"]:
                            await listener.emit("response_done", None)
                    except Exception as e:
                        print(chunk[0])
                        error = json.loads(chunk[0])
                        if error["error_code"]:
                            raise Exception(error)

async def handle_response(listener, runtime_ctx, worker_agent):
    buffer = {
        "message": { "role": "assistant", "content": "" },
    }    
    async def handle_response_delta(delta_data):
        await listener.emit("delta_full_data", delta_data)
        if "result" in delta_data:
            await listener.emit("delta", delta_data["result"])
            buffer["message"]["content"] += delta_data["result"]
        return

    listener.on("response_delta", handle_response_delta)

    async def handle_response_done(done_data):
        if done_data != None:
            await listener.emit("done_full_data", done_data)
            content = done_data["result"]
            prompt_output_format = runtime_ctx.get("prompt_output_format")
            content = await loads_and_fix(content, prompt_output_format, worker_agent=worker_agent, is_debug=runtime_ctx.get("is_debug"))
            await listener.emit("done", content)
        else:
            await listener.emit("done_full_data", buffer)
            await listener.emit("done", buffer["message"]["content"])

    listener.on("response_done", handle_response_done)