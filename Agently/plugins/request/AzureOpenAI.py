from .utils import RequestABC, to_prompt_structure, to_instruction, to_json_desc
from openai import AsyncAzureOpenAI
from Agently.utils import RuntimeCtxNamespace
import httpx
import time

class AzureOpenAI(RequestABC):
    def __init__(self, request):
        self.request = request
        self.use_assistant = False
        self.assistant_id = None
        self.model_name = "AzureOpenAI"
        self.model_settings = RuntimeCtxNamespace(f"model.{ self.model_name }", self.request.settings)
        self.request_type = self.request.request_runtime_ctx.get("request_type", "chat")
        if self.request_type == None:
            self.request_type = "chat"

    def _create_client(self):
        client_params = {}
        httpx_client = self.model_settings.get_trace_back("httpx_client")
        if httpx_client:
            httpx_client.headers.update({ "Connection": "close" })
            client_params.update({ "http_client": httpx_client })
        else:
            proxy = self.request.settings.get_trace_back("proxy")
            verify = self.model_settings.get_trace_back("verify")
            httpx_options = self.model_settings.get_trace_back("httpx.options", {})
            httpx_params = httpx_options
            httpx_params.update({
                "headers": [("Connection", "close")],
            })
            # verify
            if verify:
                httpx_params.update({ "verify": verify })
            # proxy
            if proxy:
                httpx_params.update({ "proxies": proxy })
            client_params.update({
                "http_client": httpx.AsyncClient(**httpx_params),
            })
        auth = self.model_settings.get_trace_back("auth", {})
        if "api_key" not in auth or "api_version" not in auth and "azure_endpoint" not in auth:
            raise Exception("[Request: AzureOpenAI] Missing required auth items: [`api_key`, `api_version`, `azure_endpoint`]. Use .set_settings('model.AzureOpenAI.auth', { 'api_key': 'xxxxxx', 'api_version': 'xxxxxx', 'azure_endpoint': 'xxxxxx' }) to state.")
        client_params.update(auth)

        client = AsyncAzureOpenAI(**client_params)
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
                    raise Exception(f"[Request] OpenAI vision model .files() can only accept string or dict.")
            request_messages.append({ "role": "user", "content": content })
        else:
            request_messages.append({ "role": "user", "content": prompt_text })
        return request_messages                

    def generate_request_data(self):
        self.use_assistant = self.model_settings.get_trace_back("use_assistant", False)
        if self.request_type == "chat" and self.use_assistant:
            assistant_id = self.model_settings.get_trace_back("assistant_id")
            if not assistant_id:
                raise Exception("[Request] OpenAI require 'assistant_id' when 'use_assistant' is True. Use agent.OpenAIAssistant.update() to create an assistant if you don't have one.")
            else:
                self.assistant_id = assistant_id
            options = self.model_settings.get_trace_back("options", {})
            if "model" not in options:
                options.update({ "model": "gpt-35-turbo" })
            return {
                "stream": True,
                "messages": self.construct_request_messages(),
                "options": options,
            }
        elif self.request_type == "chat":
            options = self.model_settings.get_trace_back("options", {})
            if "model" not in options:
                options.update({ "model": "gpt-35-turbo" })
            return {
                "stream": True,
                "messages": self.construct_request_messages(),
                **options
            }
        elif self.request_type == "vision":
            options = self.model_settings.get_trace_back("options", {})
            if "model" not in options:
                options.update({ "model": "gpt-4" })
            return {
                "stream": True,
                "messages": self.construct_request_messages(),
                **options
            }

    async def request_assiatant(self, request_data: dict):
        client = self._create_client()
        # create thread
        thread = await client.beta.threads.create(
            messages = request_data["messages"]
        )
        # create run
        run = await client.beta.threads.runs.create(
            thread_id = thread.id,
            assistant_id = self.assistant_id,
            **request_data["options"]
        )
        # wait until run finished
        is_complete = False
        retrieved_run = None
        while not is_complete:
            time.sleep(1)
            retrieved_run = await client.beta.threads.runs.retrieve(
                run_id = run.id,
                thread_id = thread.id,
            )
            if retrieved_run.status in ("completed", "requires_action"):
                is_complete = True
        # retrieve run step
        retrieved_run_steps = await client.beta.threads.runs.steps.list(
            run_id = run.id,
            thread_id = thread.id,
        )
        message_id = None
        # find complete or requires_action step to get message_id
        for step in retrieved_run_steps.data:
            if step.status in ("completed", "requires_action"):
                message_id = step.step_details.message_creation.message_id
                break
        # retrieve message
        message = await client.beta.threads.messages.retrieve(
            message_id = message_id,
            thread_id = thread.id,
        )
        # finally we get it...
        return message.content[0].text.value

    async def request_gpt(self, request_data: dict):
        client = self._create_client()
        #if self.request.request_runtime_ctx.get("response:type") == "JSON":
            #request_data.update({ "response_format": { "type": "json_object" } })
        stream = await client.chat.completions.create(
            **request_data
        )
        return stream

    async def request_vision(self, request_data: dict):
        client = self._create_client()
        request_data["max_tokens"] = 4096
        stream = await client.chat.completions.create(
            **request_data
        )
        return stream

    async def request_model(self, request_data: dict):
        if self.use_assistant and self.request_type == "chat":
            return await self.request_assiatant(request_data)
        elif self.request_type == "chat":
            return await self.request_gpt(request_data)
        elif self.request_type == "vision":
            return await self.request_vision(request_data)

    async def broadcast_response_without_streaming(self, response):
        yield({ "event": "response:done", "data": response })

    async def broadcast_response_with_streaming(self, response_generator):
        response_message = {}
        async for part in response_generator:
            if "choices" in dir(part) and isinstance(part.choices, list) and len(part.choices) > 0:
                delta = dict(part.choices[0].delta)
                for key, value in delta.items():
                    if key not in response_message:
                        response_message[key] = value or ""
                    else:
                        response_message[key] += value or ""
                yield({ "event": "response:delta_origin", "data": part })
                yield({ "event": "response:delta", "data": part.choices[0].delta.content or "" })
            else:
                if self.request.settings.get_trace_back("is_debug"):
                    print(f"[Request] Azure OpenAI Server Response Message: { str(dict(part)) }")
                yield({ "event": "response:delta_origin", "data": part })
        yield({ "event": "response:done_origin", "data": response_message })
        yield({ "event": "response:done", "data": response_message["content"] })

    async def broadcast_response(self, response_generator):
        if self.use_assistant and self.request_type == "chat":
            return self.broadcast_response_without_streaming(response_generator)
        elif self.request_type == "chat":
            return self.broadcast_response_with_streaming(response_generator)
        elif self.request_type == "vision":
            return self.broadcast_response_with_streaming(response_generator)

    def export(self):
        return {
            "generate_request_data": self.generate_request_data,
            "request_model": self.request_model,
            "broadcast_response": self.broadcast_response,
        }

def export():
    return ("AzureOpenAI", AzureOpenAI)