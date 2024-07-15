from .utils import RequestABC, to_prompt_structure, to_instruction, to_json_desc
from openai import AsyncOpenAI as OpenAIClient
from Agently.utils import RuntimeCtxNamespace
import httpx


class PerfXCloud(RequestABC):
    def __init__(self, request):
        self.request = request
        self.model_name = "PerfXCloud"
        self.model_settings = RuntimeCtxNamespace(f"model.{self.model_name}", self.request.settings)
        self.request_type = self.request.request_runtime_ctx.get("request_type", "chat")
        if self.request_type is None:
            self.request_type = "chat"

    def _create_client(self):
        # 初始化客户端参数
        client_params = {
            "base_url": "https://cloud.perfxlab.cn/v1",
        }
        # 如果设置中指定了基本URL，则更新基本URL
        base_url = self.model_settings.get_trace_back("url")
        if (base_url):
            client_params.update({"base_url": base_url})
        # 可选配置代理设置
        proxy = self.request.settings.get_trace_back("proxy")
        if (proxy):
            client_params.update({"http_client": httpx.Client(proxies=proxy)})
        # 设置API密钥进行认证
        api_key = self.model_settings.get_trace_back("auth.api_key")
        if (api_key):
            client_params.update({"api_key": api_key})
        else:
            raise Exception(
                "[Request] PerfXCloud require api_key. use .set_auth({ 'api_key': '<Your-API-Key>' }) to set it.")
        client = OpenAIClient(**client_params)
        return client

    def construct_request_messages(self):
        # 初始化请求消息
        request_messages = []

        # 如果有通用指令，则添加
        general_instruction_data = self.request.request_runtime_ctx.get_trace_back("prompt.general")
        if general_instruction_data:
            request_messages.append(
                {"role": "system", "content": f"[GENERAL INSTRUCTION]\n{to_instruction(general_instruction_data)}"})

        # 如果有角色设置，则添加
        role_data = self.request.request_runtime_ctx.get_trace_back("prompt.role")
        if role_data:
            request_messages.append({"role": "system", "content": f"[ROLE SETTINGS]\n{to_instruction(role_data)}"})

        # 如果有用户信息，则添加
        user_info_data = self.request.request_runtime_ctx.get_trace_back("prompt.user_info")
        if user_info_data:
            request_messages.append({"role": "system", "content": f"[ABOUT USER]\n{to_instruction(user_info_data)}"})

        # 如果有摘要信息，则添加
        headline_data = self.request.request_runtime_ctx.get_trace_back("prompt.abstract")
        if headline_data:
            request_messages.append({"role": "assistant", "content": to_instruction(headline_data)})

        # 如果有聊天历史记录，则添加
        chat_history_data = self.request.request_runtime_ctx.get_trace_back("prompt.chat_history")
        if chat_history_data:
            request_messages.extend(chat_history_data)

        # 提取各种与提示相关的数据
        prompt_input_data = self.request.request_runtime_ctx.get_trace_back("prompt.input")
        prompt_info_data = self.request.request_runtime_ctx.get_trace_back("prompt.info")
        prompt_instruct_data = self.request.request_runtime_ctx.get_trace_back("prompt.instruct")
        prompt_output_data = self.request.request_runtime_ctx.get_trace_back("prompt.output")

        # 如果有文件数据，则提取
        files_data = self.request.request_runtime_ctx.get_trace_back("prompt.files")

        # 确保至少有一个与提示相关的数据可用
        if not prompt_input_data and not prompt_info_data and not prompt_instruct_data and not prompt_output_data:
            raise Exception(
                "[Request] Missing 'prompt.input', 'prompt.info', 'prompt.instruct', 'prompt.output' in request_runtime_ctx. At least set value to one of them.")

        # 根据可用数据构造提示文本
        prompt_text = ""
        if prompt_input_data and not prompt_info_data and not prompt_instruct_data and not prompt_output_data:
            prompt_text = to_instruction(prompt_input_data)
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
                    prompt_dict["[OUTPUT REQUIREMENT]"] = str(prompt_output_data)
            prompt_text = to_prompt_structure(prompt_dict, end="[OUTPUT]:\n")

        # 对于视觉模型，包含文件数据
        if self.request_type == "vision":
            content = []
            content.append({"type": "text", "text": prompt_text})
            for image_content in files_data:
                if isinstance(image_content, str):
                    content.append({"type": "image_url", "image_url": {"url": image_content}})
                elif isinstance(image_content, dict):
                    content.append({"type": "image_url", "image_url": image_content})
                else:
                    raise Exception(f"[Request] PerfXCloud vision model .files() can only accept string or dict.")
            request_messages.append({"role": "user", "content": content})
        else:
            request_messages.append({"role": "user", "content": prompt_text})

        return request_messages

    def generate_request_data(self):
        # 从设置中获取模型选项
        options = self.model_settings.get_trace_back("options", {})
        if "model" not in options:
            options.update({"model": "Llama3-Chinese_v2"})

        # 为聊天模型生成请求数据
        if self.request_type == "chat":
            return {
                "stream": True,
                "messages": self.construct_request_messages(),
                **options
            }
        elif self.request_type == "vision":
            raise Exception("[Request] PerfXCloud does not support vision")

    async def request_model(self, request_data: dict):
        # 创建客户端并向聊天模型发出请求
        client = self._create_client()
        stream = await client.chat.completions.create(
            **request_data
        )
        return stream

    async def broadcast_response(self, response_generator):
        # 初始化响应消息
        response_message = {}
        async for part in response_generator:
            delta = dict(part.choices[0].delta)
            for key, value in delta.items():
                if key not in response_message:
                    response_message[key] = value or ""
                else:
                    response_message[key] += value or ""
            # 传递中间响应部分
            yield ({"event": "response:delta_origin", "data": part})
            yield ({"event": "response:delta", "data": part.choices[0].delta.content or ""})
        # 传递最终响应消息
        yield ({"event": "response:done_origin", "data": response_message})
        yield ({"event": "response:done", "data": response_message["content"]})

    def export(self):
        return {
            "generate_request_data": self.generate_request_data,
            "request_model": self.request_model,
            "broadcast_response": self.broadcast_response,
        }


def export():
    return ("PerfXCloud", PerfXCloud)
