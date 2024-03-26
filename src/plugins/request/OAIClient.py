from openai import AsyncOpenAI as OpenAIClient
from .utils import RequestABC, to_prompt_structure, to_instruction, to_json_desc, find_json
from Agently.utils import RuntimeCtxNamespace
import httpx
import json

class OAIClient(RequestABC):
    def __init__(self, request):
        self.request = request
        self.model_name = "OAIClient"
        self.model_settings = RuntimeCtxNamespace(f"model.{ self.model_name }", self.request.settings)
        self.request_type = self.request.request_runtime_ctx.get("request_type", "chat")
        self.default_options = {
            "stream": True
        }
        self.message_rules = {
            "no_multi_system_messages": True, # Will combine multi system messages into one message
            "strict_orders": True, # Will arrange message in orders like "user-assisantant-user-assisntant-..."
        }

    def construct_request_messages(self):
        #init request messages
        request_messages = []
        # - general instruction
        general_instruction_data = self.request.request_runtime_ctx.get_trace_back("prompt.general_instruction")
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
        # - headline
        headline_data = self.request.request_runtime_ctx.get_trace_back("prompt.headline")
        if headline_data:
            request_messages.append({ "role": "assistant", "content": [{"type": "text", "text": f"[ABSTRACT]\n{ to_instruction(headline_data) }" }] })
        # - chat history
        chat_history_data = self.request.request_runtime_ctx.get_trace_back("prompt.chat_history")
        if chat_history_data:
            request_messages.extend(chat_history_data)
        # - request message (prompt)
        prompt_input_data = self.request.request_runtime_ctx.get_trace_back("prompt.input")
        prompt_information_data = self.request.request_runtime_ctx.get_trace_back("prompt.information")
        prompt_instruction_data = self.request.request_runtime_ctx.get_trace_back("prompt.instruction")
        prompt_output_data = self.request.request_runtime_ctx.get_trace_back("prompt.output")
        # --- only input
        if not prompt_input_data and not prompt_information_data and not prompt_instruction_data and not prompt_output_data:
            raise Exception("[Request] Missing 'prompt.input', 'prompt.information', 'prompt.instruction', 'prompt.output' in request_runtime_ctx. At least set value to one of them.")
        prompt_text = ""
        if prompt_input_data and not prompt_information_data and not prompt_instruction_data and not prompt_output_data:
            prompt_text = to_instruction(prompt_input_data)
        # --- construct prompt
        else:
            prompt_dict = {}
            if prompt_input_data:
                prompt_dict["[INPUT]"] = to_instruction(prompt_input_data)
            if prompt_information_data:
                prompt_dict["[HELPFUL INFORMATION]"] = str(prompt_information_data)
            if prompt_instruction_data:
                prompt_dict["[INSTRUCTION]"] = to_instruction(prompt_instruction_data)
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

    def format_request_messages(self, request_messages):
        system_prompt = ""
        system_messages = []
        chat_messages = []
        role_list = ["user", "assistant"]
        current_role = 0
        for message in request_messages:
            if message["role"] == "system":
                # no_multi_system_messages=True
                if self.message_rules["no_multi_system_messages"]:
                    system_prompt += f"{ message['content'] }\n"
                # no_multi_system_messages=False
                else:
                    system_messages.append(message)
            else:
                # strict_orders=True
                if self.message_rules["strict_orders"]:
                    if len(chat_messages) == 0 and message["role"] != "user":
                        chat_messages.append({ "role": "user", "content": "What did we talked about?" })
                        current_role = not current_role
                    if message["role"] == role_list[current_role]:
                        chat_messages.append(message)
                        current_role = not current_role
                    else:
                        content = f"{ chat_messages[-1]['content'] }\n{ message['content'] }"
                        chat_messages[-1]['content'] = content
                # strict_orders=False
                else:
                    chat_messages.append(message)
        # no_multi_system_messages=True
        if self.message_rules["no_multi_system_messages"] and system_prompt != "":
            system_messages.append({ "role": "system", "content": system_prompt })
        formatted_messages = system_messages.copy()
        formatted_messages.extend(chat_messages)
        return formatted_messages

    def construct_completion_prompt(self):
        # - init prompt
        completion_prompt = ""
        # - general instruction
        general_instruction_data = self.request.request_runtime_ctx.get_trace_back("prompt.general_instruction")
        if general_instruction_data:
            completion_prompt += f"[GENERAL INSTRUCTION]\n{ to_instruction(general_instruction_data) }\n"
        # - role
        role_data = self.request.request_runtime_ctx.get_trace_back("prompt.role")
        if role_data:
            completion_prompt += f"[ROLE SETTINGS]\n{ to_instruction(role_data) }\n"
        # - user info
        user_info_data = self.request.request_runtime_ctx.get_trace_back("prompt.user_info")
        if user_info_data:
            completion_prompt += f"[ABOUT USER]\n{ to_instruction(user_info_data) }\n"
        # - headline
        headline_data = self.request.request_runtime_ctx.get_trace_back("prompt.headline")
        if headline_data:
            completion_prompt += f"[ABSTRACT]\n{ to_instruction(headline_data) }\n"
        # - main prompt
        chat_history_data = self.request.request_runtime_ctx.get_trace_back("prompt.chat_history")
        prompt_input_data = self.request.request_runtime_ctx.get_trace_back("prompt.input")
        prompt_information_data = self.request.request_runtime_ctx.get_trace_back("prompt.information")
        prompt_instruction_data = self.request.request_runtime_ctx.get_trace_back("prompt.instruction")
        prompt_output_data = self.request.request_runtime_ctx.get_trace_back("prompt.output")
        if not prompt_input_data and not prompt_information_data and not prompt_instruction_data and not prompt_output_data and not chat_history_data:
            raise Exception("[Request] Missing 'prompt.chat_history', 'prompt.input', 'prompt.information', 'prompt.instruction', 'prompt.output' in request_runtime_ctx. At least set value to one of them.")
        # --- only input
        if prompt_input_data and not chat_history_data and not prompt_information_data and not prompt_instruction_data and not prompt_output_data:
            if completion_prompt == "":
                completion_prompt += to_instruction(prompt_input_data)
            else:
                completion_prompt += f"[OUTPUT]\n{ to_instruction(prompt_input_data) }"
        # --- construct prompt
        else:
            # - with output format
            if isinstance(prompt_output_data, (dict, list, set)):
                prompt_dict = {}
                if chat_history_data:
                    prompt_dict["[HISTORY LOGS]"] = ""
                    for message in chat_history_data:
                        prompt_dict["[HISTORY LOGS]"] += f"{ message['role'] }: { message['content'] }\n"
                if prompt_input_data:
                    prompt_dict["[INPUT]"] = to_instruction(prompt_input_data)
                if prompt_information_data:
                    prompt_dict["[HELPFUL INFORMATION]"] = str(prompt_information_data)
                if prompt_instruction_data:
                    prompt_dict["[INSTRUCTION]"] = to_instruction(prompt_instruction_data)
                if prompt_output_data:
                    prompt_dict["[OUTPUT REQUIREMENT]"] = {
                        "TYPE": "JSON can be parsed in Python",
                        "FORMAT": to_json_desc(prompt_output_data),
                    }
                    self.request.request_runtime_ctx.set("response:type", "JSON")
                completion_prompt += to_prompt_structure(
                    prompt_dict,
                    end="[OUTPUT]:\nassistant: "
                        if chat_history_data and len(chat_history_data) > 0
                        else "[OUTPUT]:\n"
                )
            # without output format
            else:
                if prompt_information_data:
                    completion_prompt += f"[HELPFUL INFORMATION]\n{ str(prompt_information_data) }\n"
                if prompt_instruction_data:
                    completion_prompt += f"[INSTRUCTION]\n{ to_instruction(prompt_instruction_data) }\n"
                if prompt_output_data:
                    completion_prompt += f"[OUTPUT REQUIREMENT]\n{ str(prompt_output_data) }\n"
                completion_prompt += "[OUTPUT]\n"
                # chat completion
                if chat_history_data:
                    for message in chat_history_data:
                        completion_prompt += f"{ message['role'] }: { message['content'] }\n"
                    if prompt_input_data:
                        completion_prompt += f"user: { to_instruction(prompt_input_data) }\n"
                    completion_prompt += "assistant: "
                # text completion
                else:
                    if prompt_input_data:
                        completion_prompt += prompt_input_data
        return completion_prompt

    def generate_request_data(self):
        # collect options
        options = self.model_settings.get_trace_back("options", {})
        for key, value in self.default_options.items():
            if key not in options:
                options.update({ key: value })
        if self.request_type == "chat":
            return {
                "messages": self.format_request_messages(self.construct_request_messages()),
                **options,
            }
        elif self.request_type == "completions":
            return {
                "prompt": self.construct_completion_prompt(),
                **options,
            }
        else:
            raise Exception(f"Can not support request type: { self.request_type }.")

    async def request_model(self, request_data: dict):
        # create client
        client_params = {}
        base_url = self.model_settings.get_trace_back("url")
        if base_url:
            client_params.update({ "base_url": base_url })
        proxy = self.model_settings.get_trace_back("proxy")
        if proxy:
            client_params.update({ "http_client": httpx.Client( proxies = proxy ) })
        api_key = self.model_settings.get_trace_back("auth.api_key")
        if api_key:
            client_params.update({ "api_key": api_key })
        else:
            client_params.update({ "api_key": "None" })
        client = OpenAIClient(**client_params)
        # request
        if self.request_type == "chat":
            stream = await client.chat.completions.create(**request_data)
        elif self.request_type == "completions":
            stream = await client.completions.create(**request_data)
        return stream

    async def broadcast_response(self, response_generator):
        if self.request_type == "chat":
            response_message = {}
            async for part in response_generator:
                delta = dict(part.choices[0].delta)
                for key, value in delta.items():
                    if key not in response_message:
                        response_message[key] = value or ""
                    else:
                        response_message[key] += value or ""
                yield({ "event": "response:delta_origin", "data": part })
                yield({ "event": "response:delta", "data": part.choices[0].delta.content or "" })
            yield({ "event": "response:done_origin", "data": response_message })
            yield({ "event": "response:done", "data": response_message["content"] })
        elif self.request_type == "completions":
            response_message = {}
            async for part in response_generator:
                delta = dict(part.choices[0])
                for key, value in delta.items():
                    if key not in response_message and value is not None:
                        response_message[key] = value
                    elif key in response_message and value is not None:
                        response_message[key] += value
                yield({ "event": "response:delta_origin", "data": delta })
                yield({ "event": "response:delta", "data": delta["text"] or "" })
            yield({ "event": "response:done_origin", "data": response_message })
            yield({ "event": "response:done", "data": response_message["text"] })
                
    def export(self):
        return {
            "generate_request_data": self.generate_request_data,
            "request_model": self.request_model,
            "broadcast_response": self.broadcast_response,
        }

def export():
    return("OAIClient", OAIClient)