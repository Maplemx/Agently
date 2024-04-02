from .utils import RequestABC, to_prompt_structure, to_instruction, to_json_desc
from openai import AsyncOpenAI as OpenAIClient
from Agently.utils import RuntimeCtxNamespace
import httpx

class Kimi(RequestABC):
    def __init__(self, request):
        self.request = request
        self.model_name = "Kimi"
        self.model_settings = RuntimeCtxNamespace(f"model.{ self.model_name }", self.request.settings)
        self.request_type = self.request.request_runtime_ctx.get("request_type", "chat")
        if self.request_type == None:
            self.request_type = "chat"

    def _create_client(self):
        client_params = {
            "base_url": "https://api.moonshot.cn/v1",
        }
        base_url = self.model_settings.get_trace_back("url")
        if base_url:
            client_params.update({ "base_url": base_url })
        proxy = self.request.settings.get_trace_back("proxy")
        if proxy:
            client_params.update({ "http_client": httpx.Client( proxies = proxy ) })
        api_key = self.model_settings.get_trace_back("auth.api_key")
        if api_key:
            client_params.update({ "api_key": api_key })
        else:
            raise Exception("[Request] Kimi require api_key. use .set_auth({ 'api_key': '<Your-API-Key>' }) to set it.")
        client = OpenAIClient(**client_params)
        return client

    def construct_request_messages(self):
        #init request messages
        request_messages = []
        # - general instruction
        general_instruction_data = self.request.request_runtime_ctx.get_trace_back("prompt.general")
        if general_instruction_data:
            request_messages.append({ "role": "system", "content": f"[GENERAL INSTRUCTION]\n{ to_instruction(general_instruction_data) }" })
        # - role
        role_data = self.request.request_runtime_ctx.get_trace_back("prompt.role")
        if role_data:
            request_messages.append({ "role": "system", "content": f"[ROLE SETTINGS]\n{ to_instruction(role_data) }" })
        # - user info
        user_info_data = self.request.request_runtime_ctx.get_trace_back("prompt.user_info")
        if user_info_data:
            request_messages.append({ "role": "system", "content": f"[ABOUT USER]\n{ to_instruction(user_info_data) }" })
        # - abstract
        headline_data = self.request.request_runtime_ctx.get_trace_back("prompt.abstract")
        if headline_data:
            request_messages.append({ "role": "assistant", "content": to_instruction(headline_data) })
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
        # --- for vision model
        if self.request_type == "vision" and files_data:
            content = []
            content.append({ "type": "text", "text": prompt_text })
            for image_content in files_data:
                if isinstance(image_content, str):
                    content.append({ "type": "image_url", "image_url": { "url": image_content } })
                elif isinstance(image_content, dict):
                    content.append({ "type": "image_url", "image_url": image_content })
                else:
                    raise Exception(f"[Request] Kimi vision model .files() can only accept string or dict.")
            request_messages.append({ "role": "user", "content": content })
        else:
            request_messages.append({ "role": "user", "content": prompt_text })
        return request_messages                

    def generate_request_data(self):
        options = self.model_settings.get_trace_back("options", {})
        if "model" not in options:
            options.update({"model": "moonshot-v1-8k"})
        if self.request_type == "chat":
            return {
                "stream": True,
                "messages": self.construct_request_messages(),
                **options
            }
        elif self.request_type == "vision":
            raise Exception("[Request] Kimi does not support vision")
            # return {
            #     "stream": True,
            #     "messages": self.construct_request_messages(),
            #     **options
            # }

    async def request_model(self, request_data: dict):
        # request_chat_model
        client = self._create_client()
        if self.request.request_runtime_ctx.get("response:type") == "JSON" and request_data["model"] in (
        "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"):
            request_data.update({"response_format": {"type": "json_object"}})
        stream = await client.chat.completions.create(
            **request_data
        )
        return stream

    async def broadcast_response(self, response_generator):
        response_message = {}
        async for part in response_generator:
            delta = dict(part.choices[0].delta)
            for key, value in delta.items():
                if key not in response_message:
                    response_message[key] = value or ""
                else:
                    response_message[key] += value or ""
            yield ({"event": "response:delta_origin", "data": part})
            yield ({"event": "response:delta", "data": part.choices[0].delta.content or ""})
        yield ({"event": "response:done_origin", "data": response_message})
        yield ({"event": "response:done", "data": response_message["content"]})

    def export(self):
        return {
            "generate_request_data": self.generate_request_data,
            "request_model": self.request_model,
            "broadcast_response": self.broadcast_response,
        }

def export():
    return ("Kimi", Kimi)