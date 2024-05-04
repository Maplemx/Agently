# 基于 MiniMax Pro 接口：https://www.minimaxi.com/document/guides/chat-model/pro/api
from .utils import RequestABC, to_prompt_structure, to_instruction, to_json_desc, find_json
from Agently.utils import RuntimeCtxNamespace
import httpx
import json

DEFAULT_AI_BOT_NAME = "智能助理"
DEFAULT_USER_NAME = "用户"
# 和身份相关的字段
REL_ROLE_KEY_NAMES = ['角色', '身份', 'role', '姓名', '名称', 'name', '扮演', 'role-playing']

class MiniMax(RequestABC):
    def __init__(self, request):
        self.request = request
        self.request_type = self.request.request_runtime_ctx.get("request_type", "chat")
        if self.request_type == None:
            self.request_type = "chat"

        self.model_name = "MiniMax"
        self.model_settings = RuntimeCtxNamespace(
            f"model.{self.model_name}", self.request.settings)
        options = self.model_settings.get_trace_back("options", {})
        self.model_version = options.get('model') or "abab5.5-chat"

        # abab5.5 模型的情况，启用 func 辅助 json 格式输出（保障结构稳定性）
        self.use_func_fix_json = self.model_version.startswith('abab5.5')

    def generate_scene_info(self):
        """标准化业务场景相关的字段"""
        req_messages = []
        req_bot_desc = []

        # 处理角色信息（包含角色名称提取和角色信息设定）
        bot_role_name = DEFAULT_AI_BOT_NAME
        role_data = self.request.request_runtime_ctx.get_trace_back(
            "prompt.role")
        if role_data:
            role_data = fix_define_to_obj(role_data, '角色信息')
            for role_key in REL_ROLE_KEY_NAMES:
                role_val = get_value_ignore_case(role_data, role_key)
                if role_val:
                    bot_role_name = role_val
                    break
            req_bot_desc.append(to_instruction(role_data))

        # 处理指令
        general_instruction_data = self.request.request_runtime_ctx.get_trace_back(
            "prompt.general")
        if general_instruction_data:
            req_bot_desc.append(
                f"[重要指导说明]{to_instruction(general_instruction_data)}")

        # 处理用户信息
        user_role_name = DEFAULT_USER_NAME
        user_info_data = self.request.request_runtime_ctx.get_trace_back(
            "prompt.user_info")
        if user_info_data:
            user_info_data = fix_define_to_obj(user_info_data, '用户信息')
            for rel_key in REL_ROLE_KEY_NAMES:
                user_val = get_value_ignore_case(user_info_data, rel_key)
                if user_val:
                    user_role_name = user_val
                    break
            req_messages.append(to_user_msg(
                f"[这是我的信息介绍]：{to_instruction(user_info_data)}", user_role_name))
            req_messages.append(to_bot_msg('收到', bot_role_name))

        # 主题摘要
        headline_data = self.request.request_runtime_ctx.get_trace_back(
            "prompt.abstract")
        if headline_data:
            req_messages.append(to_user_msg(
                f"[这是我们要聊的话题]：{to_instruction(headline_data)}", user_role_name))
            req_messages.append(to_bot_msg('收到', bot_role_name))

        # 历史信息
        chat_history_data = self.request.request_runtime_ctx.get(
            "prompt.chat_history")
        if chat_history_data:
            req_messages.extend(fix_history(
                chat_history_data,
                user_name=user_role_name,
                robot_name=bot_role_name
            ))

        # - request message (prompt)
        prompt_input_data = self.request.request_runtime_ctx.get(
            "prompt.input")
        prompt_info_data = self.request.request_runtime_ctx.get(
            "prompt.info")
        prompt_instruct_data = self.request.request_runtime_ctx.get(
            "prompt.instruct")
        prompt_output_data = self.request.request_runtime_ctx.get(
            "prompt.output")
        # --- only input
        if not prompt_input_data and not prompt_info_data and not prompt_instruct_data and not prompt_output_data:
            raise Exception(
                "[Request] Missing 'prompt.input', 'prompt.info', 'prompt.instruct', 'prompt.output' in request_runtime_ctx. At least set value to one of them.")

        func_args = {}
        prompt_dict = {}
        if prompt_info_data:
            prompt_dict["[补充信息]"] = str(prompt_info_data)
        if prompt_instruct_data:
            prompt_dict["[处理规则]"] = to_instruction(prompt_instruct_data)

        if prompt_output_data:
            if isinstance(prompt_output_data, (dict, list, set)):
                # 采用 func 辅助修正格式
                if self.use_func_fix_json:
                    func_args["functions"] = [{
                        "name": "output_result",
                        "description": "输出结果",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "result": {
                                    "type": "object",
                                    "description": to_json_desc(prompt_output_data)
                                }
                            },
                            "required": [ "result" ]
                        }
                    }]
                    func_args['function_call'] = {
                        "type": "specific",
                        "name": "output_result"
                    }
                # 常规场景
                else:
                    prompt_dict["[输出要求]"] = {
                        "TYPE": "可被解析的JSON字符串",
                        "FORMAT": to_json_desc(prompt_output_data),
                    }

                self.request.request_runtime_ctx.set("response:type", "JSON")
            else:
                prompt_dict["[输出要求]"] = str(prompt_output_data)

        if len(prompt_dict) > 0:
            req_bot_desc.append(to_prompt_structure(prompt_dict))

        # 处理输入
        req_messages.append(to_user_msg(
            to_instruction(prompt_input_data), user_role_name))

        # 兜底 prompt
        if len(req_bot_desc) == 0:
            req_bot_desc.append(f"尽可能准确且专业地回答用户问题")
        
        return {
            **func_args,
            "bot_setting": [{
                "bot_name": bot_role_name,
                "content": '\n----\n'.join(req_bot_desc)
            }],
            "reply_constraints": {
                "sender_type": "BOT",
                "sender_name": bot_role_name
            },
            "messages": req_messages
        }

    def generate_request_data(self):
        options = self.model_settings.get_trace_back("options", {})
        scene_info = self.generate_scene_info()

        return {
            **scene_info,
            **options,
            "model": self.model_version,
            "stream": True
        }

    async def request_model(self, request_data: dict):
        group_id = self.model_settings.get_trace_back("auth.group_id")
        api_key = self.model_settings.get_trace_back("auth.api_key")

        if not group_id or not api_key:
            raise Exception(
                "[Request] Missing 'auth.group_id', 'auth.api_key' in model_settings. At least set value to one of them.")

        proxy = self.request.settings.get_trace_back("proxy")
        client_params = {}
        if proxy:
            client_params["proxy"] = proxy

        async with httpx.AsyncClient(**client_params) as client:
            async with client.stream(
                "POST",
                f"https://api.minimax.chat/v1/text/chatcompletion_pro?GroupId={group_id}",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                data=json.dumps(request_data).encode()
            ) as response:
                async for chunk in response.aiter_lines():
                    yield chunk

    async def broadcast_response(self, response_generator):
        full_res = ''
        full_res_raw = {}
        delta_content = ''
        old_delta_content = ''
        async for part in response_generator:
            origin_part = part[6:] if part.startswith('data:') else part
            if origin_part:
                chunk = json.loads(origin_part)
                # 异常判断
                if chunk.get('base_resp') and chunk.get('base_resp').get('status_code'):
                    raise Exception(f"[Response Error]{json.dumps(chunk.get('base_resp'))}")

                content_chunk = chunk['choices'][0]
                content_chunk_message = content_chunk['messages'][0]
                function_call_chunk = content_chunk_message.get('function_call')

                # func 辅助的场景
                if self.use_func_fix_json and function_call_chunk:
                    delta_content = extract_res_from_func_call(
                        function_call_chunk.get('arguments')
                    )
                    
                    if delta_content:
                        # 此处是直接替换的
                        full_res = delta_content
                        # 尝试计算出增量
                        delta_content = full_res[len(old_delta_content):]
                        old_delta_content = full_res

                    # 计算结束
                    if content_chunk.get('finish_reason') == 'stop':
                        full_res_raw = chunk
                        full_chunk_content = extract_res_from_func_call(
                            (content_chunk_message.get(
                                'function_call') or {}).get('arguments')
                        )
                    else:
                        yield ({"event": "response:delta_origin", "data": chunk})
                        yield ({"event": "response:delta", "data": delta_content})
                # 常规场景
                else:
                    full_res_raw = chunk
                    full_chunk_content = content_chunk['messages'] or []
                    delta_content = full_chunk_content[0]['text']
                    
                    if content_chunk.get('finish_reason') != 'stop':
                        full_res += delta_content
                        yield ({"event": "response:delta_origin", "data": chunk})
                        yield ({"event": "response:delta", "data": delta_content})

        yield ({"event": "response:done_origin", "data": full_res_raw})
        yield ({"event": "response:done", "data": full_res})

    def export(self):
        return {
            "generate_request_data": self.generate_request_data,
            "request_model": self.request_model,
            "broadcast_response": self.broadcast_response,
        }


# 修复定义信息
def fix_define_to_obj(value, default_key = '信息'):
    if isinstance(value, str):
        return {
            default_key: value
        }
    return value

# 忽略大小写，从 dict 中获取对应键的值
def get_value_ignore_case(dictionary, key):
    for k, v in dictionary.items():
        if k.lower() == key.lower():
            return v
    return None

# 用户消息体构建
def to_user_msg(msg, user_name):
    return {"sender_type": "USER", "sender_name": user_name, "text": msg}

# 回复消息体构建
def to_bot_msg(msg, bot_name):
    return {"sender_type": "BOT", "sender_name": bot_name, "text": msg}

# 将标准历史消息转成 MiniMax 适配的格式
def fix_history(chat_history, user_name = '', robot_name = ''):
    def fix(chat_item):
        return {
            "sender_type": 'USER' if chat_item['role'] == 'user' else 'BOT',
            "sender_name": user_name if chat_item['role'] == 'user' else robot_name,
            "text": chat_item['content']
        }
    return map(fix, chat_history)

# 从 function call 中获取参数数据
def extract_res_from_func_call(args_str: str):
    return (args_str or '').replace("result=", "", 1)

# 主导出函数
def export():
    return "MiniMax", MiniMax
