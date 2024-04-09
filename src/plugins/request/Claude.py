from .utils import RequestABC, to_prompt_structure, to_instruction, to_json_desc, find_json, format_request_messages
from Agently.utils import RuntimeCtxNamespace
import httpx
import json

class Claude(RequestABC):
    def __init__(self, request):
        self.request = request
        self.model_name = "Claude"
        self.model_settings = RuntimeCtxNamespace(f"model.{ self.model_name }", self.request.settings)
        if not self.model_settings.get_trace_back("message_rules.no_multi_system_messages"):
            self.model_settings.set("message_rules.no_multi_system_messages", False)
        if not self.model_settings.get_trace_back("message_rules.strict_orders"):
            self.model_settings.set("message_rules.strict_orders", True)
        if not self.model_settings.get_trace_back("message_rules.no_multi_type_messages"):
            self.model_settings.set("message_rules.no_multi_type_messages", False)
        self.default_options = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 4096,
            "stream": True,
        }
    
    def construct_request_messages(self):
        #init request messages
        request_messages = []
        # - general instruction
        general_instruction_data = self.request.request_runtime_ctx.get_trace_back("prompt.general")
        if general_instruction_data:
            request_messages.append({ "role": "system", "content": [{"type": "text", "text": f"[GENERAL INSTRUCTION]\n{ to_instruction(general_instruction_data) }" }] })
        # - role
        role_data = self.request.request_runtime_ctx.get_trace_back("prompt.role")
        if role_data:
            request_messages.append({ "role": "system", "content": [{"type": "text", "text": f"[ROLE SETTINGS]\n{ to_instruction(role_data) }" }] })
        # - user info
        user_info_data = self.request.request_runtime_ctx.get_trace_back("prompt.user_info")
        if user_info_data:
            request_messages.append({ "role": "system", "content": [{"type": "text", "text": f"[ABOUT USER]\n{ to_instruction(user_info_data) }" }] })
        # - abstract
        headline_data = self.request.request_runtime_ctx.get_trace_back("prompt.abstract")
        if headline_data:
            request_messages.append({ "role": "assistant", "content": [{"type": "text", "text": to_instruction(headline_data) }] })
        # - chat history
        chat_history_data = self.request.request_runtime_ctx.get_trace_back("prompt.chat_history")
        if chat_history_data:
            request_messages.extend(chat_history_data)
        # - request message (prompt)
        prompt_input_data = self.request.request_runtime_ctx.get_trace_back("prompt.input")
        prompt_info_data = self.request.request_runtime_ctx.get_trace_back("prompt.info")
        prompt_instruct_data = self.request.request_runtime_ctx.get_trace_back("prompt.instruct")
        prompt_output_data = self.request.request_runtime_ctx.get_trace_back("prompt.output")
        # - files
        files_data = self.request.request_runtime_ctx.get_trace_back("prompt.files")
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
                prompt_dict["[HELPFUL INFORMATION]"] = str(prompt_info_data)
            if prompt_instruct_data:
                prompt_dict["[INSTRUCTION]"] = to_instruction(prompt_instruct_data)
            if prompt_output_data:
                if isinstance(prompt_output_data, (dict, list, set)):
                    prompt_dict["[OUTPUT REQUIREMENT]"] = {
                        "TYPE": "JSON can be parsed in Python",
                        "FORMAT": to_json_desc(prompt_output_data),
                    }
                    self.request.request_runtime_ctx.set("response:type", "JSON")
                else:
                    prompt_dict["[OUTPUT REQUIERMENT]"] = str(prompt_output_data)
            prompt_text = to_prompt_structure(prompt_dict, end="[OUTPUT]:\n")
        request_messages.append({ "role": "user", "content": [{"type": "text", "text": prompt_text }] })
        return request_messages

    

    def generate_request_data(self):
        options = self.model_settings.get_trace_back("options", {})
        return {
            "messages": format_request_messages(self.construct_request_messages(), self.model_settings),
            "options": options,
        }

    async def request_model(self, request_data: dict):
        api_key = self.model_settings.get_trace_back("auth.api_key")
        base_url = self.model_settings.get_trace_back("url", "https://api.anthropic.com/v1")
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        proxy = self.request.settings.get_trace_back("proxy")
        messages = request_data["messages"]
        system_prompt = ""
        request_messages = []
        for message in messages:
            if message["role"] == "system":
                system_prompt += f"{ message['content'][0]['text'] }\n"
            else:
                request_messages.append(message)
        options = request_data["options"]
        if system_prompt != "":
            options.update({ "system": system_prompt })
        for key, value in self.default_options.items():
            if key not in options:
                options.update({ key: value })
        request_params = {
            "headers": {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            "data": json.dumps({ "messages": request_messages, **options }),
            "timeout": None,
        }
        client_params = {}
        if proxy:
            client_params["proxy"] = proxy
        async with httpx.AsyncClient(**client_params) as client:
            async with client.stream(
                "POST",
                f"{ base_url }/messages",
                **request_params
            ) as response:
                async for chunk in response.aiter_lines():
                    yield chunk

    async def broadcast_response(self, response_generator):
        full_message = {}
        buffer = ""
        async for chunk in response_generator:
            if chunk.startswith("data: "):
                content = json.loads(chunk[6:])
                yield({ "event": "response:delta_origin", "data": content })
                if content["type"] == "message_start":
                    full_message.update(content["message"])
                if content["type"] == "content_block_delta":
                    delta = content["delta"]["text"]
                    if delta is not None:
                        yield({ "event": "response:delta", "data": delta })
                        buffer += delta
                if content["type"] == "message_delta":
                    full_message.update(content["delta"])
                if content["type"] == "message_stop":
                    full_message["content"].append({ "type": "text", "text": buffer })
                    yield({ "event": "response:done_origin", "data": full_message })
                    yield({ "event": "response:done", "data": buffer })

    def export(self):
        return {
            "generate_request_data": self.generate_request_data,
            "request_model": self.request_model,
            "broadcast_response": self.broadcast_response,
        }

def export():
    return ("Claude", Claude)