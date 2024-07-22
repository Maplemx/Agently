import json
import types
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

from .utils import RequestABC, to_prompt_structure, to_instruction, to_json_desc, find_json, format_request_messages
from Agently.utils import RuntimeCtxNamespace

class Hunyuan(RequestABC):
    def __init__(self, request):
        self.request = request
        self.model_name = 'Hunyuan'
        self.model_settings = RuntimeCtxNamespace(f"model.{self.model_name}", self.request.settings)
        self.request_type = self.request.request_runtime_ctx.get('request_type', 'chat')
        self.default_options = {
            "model": "hunyuan-standard",
            "stream": True,
        }
        if not self.model_settings.get_trace_back("message_rules.no_multi_system_messages"):
            self.model_settings.set("message_rules.no_multi_system_messages", True)
        if not self.model_settings.get_trace_back("message_rules.strict_orders"):
            self.model_settings.set("message_rules.strict_orders", True)
        if not self.model_settings.get_trace_back("message_rules.no_multi_type_messages"):
            self.model_settings.set("message_rules.no_multi_type_messages", True)
    
    def construct_request_messages(self):
        #init request messages
        request_messages = []
        # - general instruction
        general_instruction_data = self.request.request_runtime_ctx.get_trace_back("prompt.general")
        if general_instruction_data:
            request_messages.append({ "role": "system", "content": [{"type": "text", "text": f"[重要指导说明]\n{ to_instruction(general_instruction_data) }" }] })
        # - role
        role_data = self.request.request_runtime_ctx.get_trace_back("prompt.role")
        if role_data:
            request_messages.append({ "role": "system", "content": [{"type": "text", "text": f"[角色及行为设定]\n{ to_instruction(role_data) }" }] })
        # - user info
        user_info_data = self.request.request_runtime_ctx.get_trace_back("prompt.user_info")
        if user_info_data:
            request_messages.append({ "role": "system", "content": [{"type": "text", "text": f"[关于和你对话的用户]\n{ to_instruction(user_info_data) }" }] })
        # - abstract
        headline_data = self.request.request_runtime_ctx.get_trace_back("prompt.abstract")
        if headline_data:
            request_messages.append({ "role": "assistant", "content": [{"type": "text", "text": f"[主题及摘要]\n{ to_instruction(headline_data) }" }] })
        # - chat history
        chat_history_data = self.request.request_runtime_ctx.get_trace_back("prompt.chat_history")
        if chat_history_data:
            request_messages.extend(chat_history_data)
        # - request message (prompt)
        prompt_input_data = self.request.request_runtime_ctx.get_trace_back("prompt.input")
        prompt_info_data = self.request.request_runtime_ctx.get_trace_back("prompt.info")
        prompt_instruct_data = self.request.request_runtime_ctx.get_trace_back("prompt.instruct")
        prompt_output_data = self.request.request_runtime_ctx.get_trace_back("prompt.output")
        # --- only input
        if not prompt_input_data and not prompt_info_data and not prompt_instruct_data and not prompt_output_data:
            raise Exception("[Request] Missing 'prompt.input', 'prompt.info', 'prompt.instruct', 'prompt.output' in request_runtime_ctx. At least set value to one of them.")
        prompt_text = ""
        if prompt_input_data and not prompt_info_data and not prompt_instruct_data and not prompt_output_data:
            prompt_text = to_instruction(prompt_input_data)
        # --- construct prompt
        else:
            prompt_dict = {}
            if prompt_input_data:
                prompt_dict["[INPUT]"] = to_instruction(prompt_input_data)
            if prompt_info_data:
                prompt_dict["[INFO]"] = str(prompt_info_data)
            if prompt_instruct_data:
                prompt_dict["[INSTRUCTION]"] = to_instruction(prompt_instruct_data)
            if prompt_output_data:
                if isinstance(prompt_output_data, (dict, list, set)):
                    prompt_dict["[OUTPUT要求]"] = {
                        "TYPE": "可被解析的JSON字符串",
                        "FORMAT": to_json_desc(prompt_output_data),
                    }
                    self.request.request_runtime_ctx.set("response:type", "JSON")
                else:
                    prompt_dict["[OUTPUT要求]"] = str(prompt_output_data)
            prompt_text = to_prompt_structure(prompt_dict, end="[OUTPUT]:\n")
        request_messages.append({ "role": "user", "content": [{"type": "text", "text": prompt_text }] })
        return request_messages

    def _uppercase_keys(self, target_dict: dict):
        if not isinstance(target_dict, dict):
            return target_dict
        uppercased_dict = {}
        for key, value in target_dict.items():
            if isinstance(value, dict):
                value = self._uppercase_keys(value)
            uppercased_dict.update({ f"{ key[:1].upper() }{ key[1:] }": value })
        return uppercased_dict

    def _uppercase_messages_keys(self, target_messages: list):
        uppercased_messages = []
        for item in target_messages:
            uppercased_item = {}
            for key, value in item.items():
                if isinstance(value, dict):
                    value = self._uppercase_keys(value)
                uppercased_item.update({ f"{ key[:1].upper() }{ key[1:] }": value })
            uppercased_messages.append(uppercased_item)
        return uppercased_messages

    def generate_request_data(self):
        options = self.default_options.copy()
        options.update(self.model_settings.get_trace_back("options", {}))
        return {
            "Messages": self._uppercase_messages_keys(
                format_request_messages( self.construct_request_messages(), self.model_settings )
            ),
            **self._uppercase_keys(options)
        }

    async def request_model(self, request_data: dict):
        auth = self.model_settings.get_trace_back("auth", {})
        auth = auth if isinstance(auth, dict) else {}
        if "secret_id" not in auth or "secret_key" not in auth:
            raise Exception("[Request] Missing 'secret_id' or 'secret_key' in auth. Use .set_settings('model.Hunyuan.auth', { 'secret_id': '***', 'secret_key': '***' }) to set it.")
        cred = credential.Credential(auth["secret_id"], auth["secret_key"])
        httpProfile = HttpProfile()
        httpProfile.endpoint = auth["endpoint"] if "endpoint" in auth else "hunyuan.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        client = hunyuan_client.HunyuanClient(cred, "", clientProfile)

        request = models.ChatCompletionsRequest()
        request.from_json_string(json.dumps(request_data))

        resp = client.ChatCompletions(request)
        if isinstance(resp, types.GeneratorType):
            for event in resp:
                yield event
        else:
            if self.request.settings.get_trace_back("is_debug"):
                print(f"[Request] Server Response Message: { str(resp) }")

    async def broadcast_response(self, response_generator):
        response_message = {}
        message_content = ""
        async for part in response_generator:
            part_data = json.loads(part["data"])
            try:
                yield({ "event": "response:delta_origin", "data": part_data })
                yield({ "event": "response:delta", "data": part_data["Choices"][0]["Delta"]["Content"] })
                message_content += part_data["Choices"][0]["Delta"]["Content"]
            except Exception as e:
                if self.request.settings.get_trace_back("is_debug"):
                    print(f"[Request] Server Response Message: { str(part_data) }")
        response_message = part_data.copy()
        response_message["Choices"][0].update({
            "Message": {
                "Role": response_message["Choices"][0]["Delta"]["Role"],
                "Content": message_content,
            }
        })
        del response_message["Choices"][0]["Delta"]
        yield({ "event": "response:done_origin", "data": response_message })
        yield({ "event": "response:done", "data": message_content })
    
    def export(self):
        return {
            "generate_request_data": self.generate_request_data,
            "request_model": self.request_model,
            "broadcast_response": self.broadcast_response,
        }

def export():
    return("Hunyuan", Hunyuan)
