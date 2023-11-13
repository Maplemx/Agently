from .utils import RequestABC, to_instruction, to_json_desc, to_prompt_structure
from Agently.utils import RuntimeCtxNamespace
import zhipuai

class ZhipuAI(RequestABC):
    def __init__(self, request):
        self.request = request
        self.model_name = "ZhipuAI"
        self.model_settings = RuntimeCtxNamespace(f"model.{ self.model_name }", self.request.settings)
        self.request_type = self.request.request_runtime_ctx.get("request_type", "chat")
        if self.request_type == None:
            self.request_type = "chat"

    def construct_request_messages(self):
        #init request messages
        request_messages = []
        # - general instruction
        general_instruction_data = self.request.request_runtime_ctx.get("prompt.general_instruction")
        if general_instruction_data:
            request_messages.append({ "role": "user", "content": f"[重要指导说明]\n{ to_instruction(general_instruction_data) }" })
            request_messages.append({ "role": "assistant", "content": "OK" })
        # - role
        role_data = self.request.request_runtime_ctx.get("prompt.role")
        if role_data and self.request_type == "chat":
            request_messages.append({ "role": "user", "content": f"[角色及行为设定]\n{ to_instruction(role_data) }" })
            request_messages.append({ "role": "assistant", "content": "OK" })
        # - user info
        user_info_data = self.request.request_runtime_ctx.get("prompt.user_info")
        if user_info_data and self.request_type == "chat":
            request_messages.append({ "role": "user", "content": f"[用户信息]\n{ to_instruction(user_info_data) }" })
            request_messages.append({ "role": "assistant", "content": "OK" })
        # - headline
        headline_data = self.request.request_runtime_ctx.get("prompt.headline")
        if headline_data:
            request_messages.append({ "role": "user", "content": f"[主题及摘要]{to_instruction(headline_data)}" })
            request_messages.append({ "role": "assistant", "content": "OK" })
        # - chat history
        chat_history_data = self.request.request_runtime_ctx.get("prompt.chat_history")
        if chat_history_data:
            request_messages.extend(chat_history_data)
        # - request message (prompt)
        prompt_input_data = self.request.request_runtime_ctx.get("prompt.input")
        prompt_information_data = self.request.request_runtime_ctx.get("prompt.information")
        prompt_instruction_data = self.request.request_runtime_ctx.get("prompt.instruction")
        prompt_output_data = self.request.request_runtime_ctx.get("prompt.output")
        # --- only input
        if not prompt_input_data and not prompt_information_data and not prompt_instruction_data and not prompt_output_data:
            raise Exception("[Request] Missing 'prompt.input', 'prompt.information', 'prompt.instruction', 'prompt.output' in request_runtime_ctx. At least set value to one of them.")
        if prompt_input_data and not prompt_information_data and not prompt_instruction_data and not prompt_output_data:
            request_messages.append({ "role": "user", "content": to_instruction(prompt_input_data) })
        # --- construct prompt
        else:
            prompt_dict = {}
            if prompt_input_data:
                prompt_dict["[输入]"] = to_instruction(prompt_input_data)
            if prompt_information_data:
                prompt_dict["[补充信息]"] = to_instruction(prompt_information_data)
            if prompt_instruction_data:
                prompt_dict["[处理规则]"] = to_instruction(prompt_instruction_data)
            if prompt_output_data:
                if isinstance(prompt_output_data, (dict, list, set)):
                    prompt_dict["[输出要求]"] = {
                        "TYPE": "JSON can be parsed in Python",
                        "FORMAT": to_json_desc(prompt_output_data),
                    }
                    self.request.request_runtime_ctx.set("response:type", "JSON")
                else:
                    prompt_dict["[输出要求]"] = str(prompt_output_data)
            request_messages.append({ "role": "user", "content": to_prompt_structure(prompt_dict, end="[输出]:\n") })
        return request_messages

    def generate_request_data(self):
        prompt = None
        options = self.model_settings.get_trace_back("options", {})
        if self.request_type == "chat":
            options["model"] = "chatglm_turbo"
            prompt = self.construct_request_messages()
            options["incremental"] = True
        if self.request_type == "character":
            options["model"] = "characterglm"
            prompt = self.construct_request_messages()
            options["incremental"] = True
            role_data = self.request.request_runtime_ctx.get("prompt.role")
            options["meta"] = {}
            if role_data:
                if "NAME" in role_data:
                    options["meta"]["bot_name"] = role_data["NAME"][0]
                    del role_data["NAME"]
                options["meta"]["bot_info"] = to_instruction(role_data)
            user_info_data = self.request.request_runtime_ctx.get("prompt.user_info")
            if user_info_data:
                if "NAME" in user_info_data:
                    options["meta"]["user_name"] = user_info_data["NAME"][0]
                    del user_info_data["NAME"]
                options["meta"]["user_info"] = to_instruction(user_info_data)
            if len(options["meta"].keys()) == 0:
                del options["meta"]
        if self.request_type == "embedding":
            options["model"] = "text_embedding"
            prompt = self.request.request_runtime_ctx.get("prompt.input")
        return {
            "prompt": prompt,
            **options
        } 

    def request_model(self, request_data: dict):
        zhipuai.api_key = self.model_settings.get_trace_back("auth.api_key")
        if self.request_type in ("chat", "character"):
            return zhipuai.model_api.sse_invoke(**request_data)
        else:
            return zhipuai.model_api.invoke(**request_data)

    def broadcast_response(self, response_generator):
        if self.request_type in ("chat", "character"):
            buffer = ""
            for part in response_generator.events():
                if part.event == "add":
                    yield({ "event": "response:delta", "data": part.data })
                    buffer += part.data
                elif part.event == "error" or part.event == "interrupted":
                    raise Exception(f"[Request] ZhipuAI Error: { part.data }")
                elif part.event == "finish":
                    yield({ "event": "response:done", "data": buffer })
                    yield({ "event": "response:done_origin", "data": { "content": buffer, "meta": part.meta } })
        elif self.request_type == "embedding":
            yield({ "event": "done", "data": response_generator["data"]["embedding"] })

    def export(self):
        return {
            "generate_request_data": self.generate_request_data,
            "request_model": self.request_model,
            "broadcast_response": self.broadcast_response,
        }

def export():
    return ("ZhipuAI", ZhipuAI)