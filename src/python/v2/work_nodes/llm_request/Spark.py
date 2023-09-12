import asyncio
import copy

import _thread as thread
import base64
import datetime
import hashlib
import hmac
import json
from urllib.parse import urlparse
import ssl
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time

import websockets

from .loads_and_fix import loads_and_fix

'''
XunFei Spark
'''
class WsParam(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, Spark_url):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.host = urlparse(Spark_url).netloc
        self.path = urlparse(Spark_url).path
        self.Spark_url = Spark_url

    # 生成url
    def create_url(self):
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + self.host + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + self.path + " HTTP/1.1"

        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()

        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'

        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": self.host
        }
        # 拼接鉴权参数，生成url
        url = self.Spark_url + '?' + urlencode(v)
        # 此处打印出建立连接时候的url,参考本demo的时候可取消上方打印的注释，比对相同参数时生成的url与自己代码生成的url是否一致
        return url

def prepare_request_data(runtime_ctx):
    #default request_data
    request_data = {
        "llm_url": "wss://spark-api.xf-yun.com/v1.1/chat",
        "data": {
            "header": {
                "uid": "0000",
            },
            "parameter": {
                "chat": {
                    "domain": "general",
                    "temperature": 0.5,
                    "max_tokens": 4096,
                    "auditing": "default"
                }
            },
        },
    }
    #check auth info
    llm_auth = runtime_ctx.get("llm_auth")
    if "Spark" in llm_auth:
        request_data["data"]["header"].update({ "app_id": llm_auth["Spark"]["app_id"] })
        request_data.update({ "llm_auth": llm_auth["Spark"] })
    else:
        raise Exception("[request]: llm_auth must be set to agent. use agent.set_llm_auth('Spark', { 'app_id': '...', 'api_secret': '...' , 'api_key': '...' }) to set.")
    #update user customize settings
    cus_llm_url = runtime_ctx.get("llm_url")
    cus_llm_url = cus_llm_url["Spark"] if cus_llm_url and "Spark" in cus_llm_url else None
    if cus_llm_url:
        request_data.update({ "llm_url": cus_llm_url })
    request_data.update({ "proxy": runtime_ctx.get("proxy") })
    cus_request_options = runtime_ctx.get("request_options")
    cus_request_options = cus_request_options["Spark"] if cus_request_options and "Spark" in cus_request_options else None
    if isinstance(cus_request_options, dict):
        for options_name, options_value in cus_request_options.items():
            request_data["data"]["parameter"]["chat"].update({ options_name: options_value })
    #get request messages
    request_messages = runtime_ctx.get("request_messages")
    #transform messages format
    for message in request_messages:
        if message["role"] == "system":
            message["role"] = "user"
    request_data["data"].update({ "messages": request_messages })
    return request_data

async def request(request_data, listener):
    response_message = { "content": "" }
    request_data["data"]["payload"] = {
        "message": {
            "text": copy.deepcopy(request_data["data"]["messages"])
        }
    }
    del request_data["data"]["messages"]

    llm_auth = request_data["llm_auth"]
    llm_url = request_data["llm_url"]
    ws_param = WsParam(llm_auth["app_id"], llm_auth["api_key"], llm_auth["api_secret"], llm_url)
    ws_url = ws_param.create_url()
    async with websockets.connect(ws_url) as websocket:
        await websocket.send(json.dumps(request_data["data"]))
        async for message in websocket:
            data = json.loads(message)
            code = data["header"]["code"]
            if code != 0:
                raise Exception("[Request Spark]:", code, data)
            else:
                choices = data["payload"]["choices"]
                await listener.emit("response:delta", choices)
                status = choices["status"]
                content = choices["text"][0]["content"]        
                response_message["content"] = response_message["content"] + content
                if status == 2:
                    del choices["text"][0]["content"]
                    response_message.update(choices["text"][0])
                    await listener.emit('response_done', response_message)       
                    return response_message

async def streaming(request_data, listener):
    return await request(request_data, listener)

async def handle_response(listener, runtime_ctx, worker_agent):
    is_streaming = runtime_ctx.get("is_streaming")
    prompt_output_format = runtime_ctx.get("prompt_output_format")
    
    async def handle_response_delta(delta_data):
        await listener.emit("extract:delta_full", delta_data)
        await listener.emit("extract:delta", delta_data["text"][0]["content"])

    listener.on("response:delta", handle_response_delta)

    async def handle_response_done(done_data):
        await listener.emit("extract:done_full", done_data)
        prompt_output_format = runtime_ctx.get("prompt_output_format")
        content = await loads_and_fix(done_data["content"], prompt_output_format, worker_agent=worker_agent, is_debug=runtime_ctx.get("is_debug"))
        await listener.emit("extract:done", content)

    listener.on("response:done", handle_response_done)