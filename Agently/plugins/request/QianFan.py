import os

from .utils import RequestABC, to_prompt_structure, to_instruction, to_json_desc, replace_placeholder_keyword, format_request_messages
from Agently.utils import RuntimeCtxNamespace
import qianfan

class Qianfan(RequestABC):
    def __init__(self, request):
        self.request = request
        self.request_type = self.request.request_runtime_ctx.get("request_type", "chat")
        if self.request_type == None:
            self.request_type = "chat"
        self.model_name = "Qianfan"
        self.model_settings = RuntimeCtxNamespace(f"model.{self.model_name}", self.request.settings)
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
            request_messages.append({ "role": "system", "content": [{"type": "text", "text": f"[用户信息]\n{ to_instruction(user_info_data) }" }] })
        # - abstract
        headline_data = self.request.request_runtime_ctx.get_trace_back("prompt.abstract")
        if headline_data:
            request_messages.append({ "role": "assistant", "content": [{"type": "text", "text": f"[主题及摘要]\n{ to_instruction(headline_data) }" }] })
        # - chat history
        chat_history_data = self.request.request_runtime_ctx.get_trace_back("prompt.chat_history")
        if chat_history_data:
            request_messages.extend(chat_history_data)
        # - request message (prompt)
        prompt_input_data = replace_placeholder_keyword("input", "输入", self.request.request_runtime_ctx.get_trace_back("prompt.input"))
        prompt_info_data = replace_placeholder_keyword("info", "补充信息", self.request.request_runtime_ctx.get_trace_back("prompt.info"))
        prompt_instruct_data = replace_placeholder_keyword("instruct", "处理规则", self.request.request_runtime_ctx.get_trace_back("prompt.instruct"))
        prompt_output_data = replace_placeholder_keyword("output", "输入", self.request.request_runtime_ctx.get_trace_back("prompt.output"))
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
                prompt_dict["[输入]"] = to_instruction(prompt_input_data)
            if prompt_info_data:
                prompt_dict["[补充信息]"] = str(prompt_info_data)
            if prompt_instruct_data:
                prompt_dict["[处理规则]"] = to_instruction(prompt_instruct_data)
            if prompt_output_data:
                if isinstance(prompt_output_data, (dict, list, set)):
                    prompt_dict["[输出要求]"] = {
                        "TYPE": "可被解析的JSON字符串",
                        "FORMAT": to_json_desc(prompt_output_data),
                    }
                    self.request.request_runtime_ctx.set("response:type", "JSON")
                else:
                    prompt_dict["[输出要求]"] = str(prompt_output_data)
            prompt_text = to_prompt_structure(prompt_dict, end="[输出]:\n")
        request_messages.append({ "role": "user", "content": [{"type": "text", "text": prompt_text }] })
        return request_messages

    def construct_completion_prompt(self):
        # - init prompt
        completion_prompt = ""
        # - general instruction
        general_instruction_data = self.request.request_runtime_ctx.get_trace_back("prompt.general")
        if general_instruction_data:
            completion_prompt += f"[重要指导说明]\n{ to_instruction(general_instruction_data) }\n"
        # - role
        role_data = self.request.request_runtime_ctx.get_trace_back("prompt.role")
        if role_data:
            completion_prompt += f"[角色及行为设定]\n{ to_instruction(role_data) }\n"
        # - user info
        user_info_data = self.request.request_runtime_ctx.get_trace_back("prompt.user_info")
        if user_info_data:
            completion_prompt += f"[用户信息]\n{ to_instruction(user_info_data) }\n"
        # - abstract
        headline_data = self.request.request_runtime_ctx.get_trace_back("prompt.abstract")
        if headline_data:
            completion_prompt += f"[主题及摘要]\n{ to_instruction(headline_data) }\n"
        # - main prompt
        chat_history_data = self.request.request_runtime_ctx.get_trace_back("prompt.chat_history")
        prompt_input_data = self.request.request_runtime_ctx.get_trace_back("prompt.input")
        prompt_info_data = self.request.request_runtime_ctx.get_trace_back("prompt.info")
        prompt_instruct_data = self.request.request_runtime_ctx.get_trace_back("prompt.instruct")
        prompt_output_data = self.request.request_runtime_ctx.get_trace_back("prompt.output")
        if not prompt_input_data and not prompt_info_data and not prompt_instruct_data and not prompt_output_data and not chat_history_data:
            raise Exception("[Request] Missing 'prompt.chat_history', 'prompt.input', 'prompt.info', 'prompt.instruct', 'prompt.output' in request_runtime_ctx. At least set value to one of them.")
        # --- only input
        if prompt_input_data and not chat_history_data and not prompt_info_data and not prompt_instruct_data and not prompt_output_data:
            if completion_prompt == "":
                completion_prompt += to_instruction(prompt_input_data)
            else:
                completion_prompt += f"[输出]\n{ to_instruction(prompt_input_data) }"
        # --- construct prompt
        else:
            # - with output format
            if isinstance(prompt_output_data, (dict, list, set)):
                prompt_dict = {}
                if chat_history_data:
                    prompt_dict["[历史会话记录]"] = ""
                    for message in chat_history_data:
                        prompt_dict["[历史会话记录]"] += f"{ message['role'] }: { message['content'] }\n"
                if prompt_input_data:
                    prompt_dict["[输入]"] = to_instruction(prompt_input_data)
                if prompt_info_data:
                    prompt_dict["[补充信息]"] = str(prompt_info_data)
                if prompt_instruct_data:
                    prompt_dict["[处理规则]"] = to_instruction(prompt_instruct_data)
                if prompt_output_data:
                    prompt_dict["[输出要求]"] = {
                        "TYPE": "可被解析的JSON字符串",
                        "FORMAT": to_json_desc(prompt_output_data),
                    }
                    self.request.request_runtime_ctx.set("response:type", "JSON")
                completion_prompt += to_prompt_structure(
                    prompt_dict,
                    end="[输出]:\nassistant: "
                        if chat_history_data and len(chat_history_data) > 0
                        else "[输出]:\n"
                )
            # without output format
            else:
                if prompt_info_data:
                    completion_prompt += f"[补充信息]\n{ str(prompt_info_data) }\n"
                if prompt_instruct_data:
                    completion_prompt += f"[处理规则]\n{ to_instruction(prompt_instruct_data) }\n"
                if prompt_output_data:
                    completion_prompt += f"[输出要求]\n{ str(prompt_output_data) }\n"
                completion_prompt += "[输出]\n"
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
        auth = self.model_settings.get_trace_back("auth", {})
        if "access_key" not in auth or "secret_key" not in auth:
            raise Exception(f"[Request] Qianfan require 'access_key' and 'secret_key'. Use .set_model_auth({{ 'access_key': <YOUR-ACCESS-KEY> }} and {{ 'secret_key': <YOUR-SECRET-KEY> }}) to set.")
        os.environ["QIANFAN_ACCESS_KEY"] = auth["access_key"]
        os.environ["QIANFAN_SECRET_KEY"] = auth["secret_key"]
        options = self.model_settings.get_trace_back("options", {})
        options = options if isinstance(options, dict) else {}
        if self.request_type == "chat":
            if "model" not in options:
                options["model"] = "ERNIE-Speed-8K"
            messages = format_request_messages(self.construct_request_messages(), self.model_settings)
            request_messages = []
            system_prompt = ""
            for message in messages:
                if message["role"] == "system":
                    system_prompt += f"{ message['content'] }\n"
                else:
                    request_messages.append(message)
            request_data = {
                "messages": request_messages,
                "stream": True,
                **options,
            }
            if system_prompt != "" and self.request.settings.get_trace_back("retry_count", 0) > 0:
                request_data.update({ "system": system_prompt })
        elif self.request_type in ["completion", "completions"]:
            if "model" not in options:
                options["model"] = "Yi-34B-Chat"
            prompt = self.construct_completion_prompt()
            request_data = {
                "prompt": prompt,
                "stream": True,
                **options
            }
        elif self.request_type in ["embedding", "embeddings"]:
            if "model" not in options:
                options["model"] = "Embedding-V1"
            content_input = (
                self.request.request_runtime_ctx.get("prompt.input")
                or self.request.request_runtime_ctx.get("prompt.texts")
            )
            if not isinstance(content_input, list):
                content_input = [content_input]
            request_data = {
                "texts": content_input,
                **options,
            }
        elif self.request_type in ["image", "images"]:
            if "model" not in options:
                options["model"] = "Stable-Diffusion-XL"
            prompt = (
                self.request.request_runtime_ctx.get("prompt.input")
                or self.request.request_runtime_ctx.get("prompt.prompt")
            )
            request_data = {
                "prompt": prompt,
                **options
            }
        elif self.request_type in ["rerank", "reranker"]:
            if "model" not in options:
                options["model"] = "bce-reranker-base_v1"
            input_data = self.request.request_runtime_ctx.get("prompt.input")
            query = (
                input_data["query"]
                if "query" in input_data
                else self.request.request_runtime_ctx.get("prompt.query")
            )
            doucments = (
                input_data["documents"]
                if "documents" in input_data
                else self.request.request_runtime_ctx.get("prompt.documents")
            )
            request_data = {
                "query": query,
                "documents": doucments,
                **options,
            }
        return request_data
    
    async def request_model(self, request_data: dict):
        if self.request_type == "chat":
            return await qianfan.ChatCompletion().ado(**request_data)
        elif self.request_type in ["completion", "completions"]:
            return await qianfan.Completion().ado(**request_data)
        elif self.request_type in ["embedding", "embeddings"]:
            return await qianfan.Embedding().ado(**request_data)
        elif self.request_type in ["image", "images"]:
            return await qianfan.Text2Image().ado(**request_data)
        elif self.request_type in ["rerank", "reranker"]:
            return await qianfan.resources.Reranker().ado(**request_data)
    
    async def broadcast_response(self, response_generator):
        if self.request_type == "chat" or self.request_type in ["completion", "completions"]:
            origin_buffer = {}
            buffer = ""
            async for part in response_generator:
                buffer += part["body"]["result"]
                origin_buffer.update(part["body"])
                yield ({ "event": "response:delta_origin", "data": part["body"] })
                yield ({ "event": "response:delta", "data": part["body"]["result"] })
            origin_buffer["result"] = buffer
            yield ({ "event": "response:done_origin", "data": origin_buffer })
            yield ({ "event": "response:done", "data": buffer })
        elif self.request_type in ["embedding", "embeddings"] or self.request_type in ["image", "images"]:
            yield({ "event": "response:done_origin", "data": response_generator["body"] })
            yield({ "event": "response:done", "data": response_generator["body"]["data"] })
        elif self.request_type in ["rerank", "reranker"]:
            yield({ "event": "response:done_origin", "data": response_generator.body })
            yield({ "event": "response:done", "data": response_generator.body["results"] })
    
    def export(self):
        return {
            "generate_request_data": self.generate_request_data,
            "request_model": self.request_model,
            "broadcast_response": self.broadcast_response,
        }


def export():
    return ("Qianfan", Qianfan)