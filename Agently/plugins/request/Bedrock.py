from .utils import RequestABC, to_prompt_structure, to_instruction, to_json_desc, find_json, format_request_messages
from Agently.utils import RuntimeCtxNamespace
import json
import boto3

class Bedrock(RequestABC):
    def __init__(self, request):
        self.request = request
        self.model_name = "Bedrock"
        self.model_settings = RuntimeCtxNamespace(f"model.{self.model_name}", self.request.settings)
        
        # Set default message rules
        if not self.model_settings.get_trace_back("message_rules.no_multi_system_messages"):
            self.model_settings.set("message_rules.no_multi_system_messages", False)
        if not self.model_settings.get_trace_back("message_rules.strict_orders"):
            self.model_settings.set("message_rules.strict_orders", True)
        if not self.model_settings.get_trace_back("message_rules.no_multi_type_messages"):
            self.model_settings.set("message_rules.no_multi_type_messages", False)
            
        # Default options for Bedrock models
        self.default_options = {
            "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
            "maxTokens": 4096,
        }
        
        # For streaming responses
        self.is_streaming = True

    def construct_request_messages(self):
        # Init request messages
        request_messages = []
        
        # General instruction
        general_instruction_data = self.request.request_runtime_ctx.get_trace_back("prompt.general")
        if general_instruction_data:
            request_messages.append({"role": "system", "content": [{"type": "text", "text": f"[GENERAL INSTRUCTION]\n{to_instruction(general_instruction_data)}"}]})
        
        # Role
        role_data = self.request.request_runtime_ctx.get_trace_back("prompt.role")
        if role_data:
            request_messages.append({"role": "system", "content": [{"type": "text", "text": f"[ROLE SETTINGS]\n{to_instruction(role_data)}"}]})
        
        # User info
        user_info_data = self.request.request_runtime_ctx.get_trace_back("prompt.user_info")
        if user_info_data:
            request_messages.append({"role": "system", "content": [{"type": "text", "text": f"[ABOUT USER]\n{to_instruction(user_info_data)}"}]})
        
        # Abstract
        headline_data = self.request.request_runtime_ctx.get_trace_back("prompt.abstract")
        if headline_data:
            request_messages.append({"role": "assistant", "content": [{"type": "text", "text": to_instruction(headline_data)}]})
        
        # Chat history
        chat_history_data = self.request.request_runtime_ctx.get_trace_back("prompt.chat_history")
        if chat_history_data:
            request_messages.extend(chat_history_data)
        
        # Request message (prompt)
        prompt_input_data = self.request.request_runtime_ctx.get_trace_back("prompt.input")
        prompt_info_data = self.request.request_runtime_ctx.get_trace_back("prompt.info")
        prompt_instruct_data = self.request.request_runtime_ctx.get_trace_back("prompt.instruct")
        prompt_output_data = self.request.request_runtime_ctx.get_trace_back("prompt.output")
        
        # Files
        files_data = self.request.request_runtime_ctx.get_trace_back("prompt.files")
        
        # Validate that at least one prompt field is set
        if not prompt_input_data and not prompt_info_data and not prompt_instruct_data and not prompt_output_data:
            raise Exception("[Request] Missing 'prompt.input', 'prompt.info', 'prompt.instruct', 'prompt.output' in request_runtime_ctx. At least set value to one of them.")
        
        prompt_text = ""
        # Only input
        if prompt_input_data and not prompt_info_data and not prompt_instruct_data and not prompt_output_data:
            prompt_text = to_instruction(prompt_input_data)
        # Construct structured prompt
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
        
        request_messages.append({"role": "user", "content": [{"type": "text", "text": prompt_text}]})
        return request_messages

    def _create_client(self):
        """Create and return a Bedrock Runtime client using AWS credentials."""
        aws_region = self.model_settings.get_trace_back("region", "us-east-1")
        aws_access_key = self.model_settings.get_trace_back("auth.access_key")
        aws_secret_key = self.model_settings.get_trace_back("auth.secret_key")
        aws_session_token = self.model_settings.get_trace_back("auth.session_token", None)
        
        if not aws_access_key or not aws_secret_key:
            raise Exception("[Bedrock] Missing AWS credentials. Use Agently.set_settings('model.Bedrock.auth', {'access_key': '<YOUR_ACCESS_KEY>', 'secret_key': '<YOUR_SECRET_KEY>'}) to set them.")
        
        credentials = {
            "aws_access_key_id": aws_access_key,
            "aws_secret_access_key": aws_secret_key,
        }
        
        if aws_session_token:
            credentials["aws_session_token"] = aws_session_token
            
        client = boto3.client(
            'bedrock-runtime',
            region_name=aws_region,
            **credentials
        )
        
        return client

    def generate_request_data(self):
        options = self.model_settings.get_trace_back("options", {})
        self.is_streaming = options.get("streaming", True)
        
        # Set streaming default
        if "streaming" not in options:
            options["streaming"] = self.is_streaming
            
        # Merge with default options
        for key, value in self.default_options.items():
            if key not in options:
                options[key] = value
        
        return {
            "messages": format_request_messages(self.construct_request_messages(), self.model_settings),
            "options": options,
        }

    async def request_model(self, request_data: dict):
        client = self._create_client()
        messages = request_data["messages"]
        options = request_data["options"]
        model_id = options.pop("modelId")
        is_streaming = options.pop("streaming") if "streaming" in options else self.is_streaming
        
        # Extract system message if present
        system_prompt = ""
        request_messages = []
        
        for message in messages:
            if message["role"] == "system":
                system_prompt += f"{message['content'][0]['text']}\n"
            else:
                request_messages.append(message)
        
        # Prepare the request body based on the model provider
        if "anthropic.claude" in model_id:
            # Claude format for Bedrock
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": options.pop("maxTokens") if "maxTokens" in options else 4096,
                "messages": request_messages
            }
            
            if system_prompt:
                body["system"] = system_prompt.strip()
                
            # Add remaining options
            for key, value in options.items():
                body[key] = value
                
        elif "amazon.titan" in model_id:
            # Titan format for Bedrock
            body = {
                "inputText": messages[-1]["content"][0]["text"],
                "textGenerationConfig": options
            }
            
        elif "meta.llama" in model_id:
            # Llama format for Bedrock
            combined_prompt = ""
            if system_prompt:
                combined_prompt += f"<system>\n{system_prompt.strip()}\n</system>\n\n"
                
            for msg in request_messages:
                role = msg["role"]
                content = msg["content"][0]["text"]
                if role == "user":
                    combined_prompt += f"<human>\n{content}\n</human>\n\n"
                elif role == "assistant":
                    combined_prompt += f"<assistant>\n{content}\n</assistant>\n\n"
            
            # Add final assistant tag for the model response
            combined_prompt += "<assistant>\n"
            
            body = {
                "prompt": combined_prompt,
                "max_gen_len": options.pop("maxTokens") if "maxTokens" in options else 4096,
            }
            
            # Add remaining options
            for key, value in options.items():
                body[key] = value
                
        else:
            # Generic format as fallback
            body = {
                "prompt": messages[-1]["content"][0]["text"],
                **options
            }
        
        # Convert body to JSON string
        body_json = json.dumps(body)
        
        if is_streaming:
            # Streaming response
            response = client.invoke_model_with_response_stream(
                modelId=model_id,
                body=body_json
            )
            
            for event in response.get('body'):
                if 'chunk' in event:
                    chunk_data = json.loads(event['chunk']['bytes'].decode())
                    yield chunk_data
        else:
            # Non-streaming response
            response = client.invoke_model(
                modelId=model_id,
                body=body_json
            )
            
            yield json.loads(response.get('body').read())

    async def broadcast_response(self, response_generator):
        if not self.is_streaming:
            # Non-streaming response
            async for response in response_generator:
                if "anthropic.claude" in self.default_options["modelId"]:
                    result = response.get("content", [{"text": ""}])[0]["text"]
                elif "amazon.titan" in self.default_options["modelId"]:
                    result = response.get("results", [{"outputText": ""}])[0]["outputText"]
                elif "meta.llama" in self.default_options["modelId"]:
                    result = response.get("generation", "")
                else:
                    result = response.get("completion", "")
                    
                yield({"event": "response:done_origin", "data": response})
                yield({"event": "response:done", "data": result})
        else:
            # Streaming response
            full_response = ""
            
            if "anthropic.claude" in self.default_options["modelId"]:
                async for chunk in response_generator:
                    yield({"event": "response:delta_origin", "data": chunk})
                    
                    if "type" in chunk and chunk["type"] == "content_block_delta":
                        delta = chunk["delta"].get("text", "")
                        if delta:
                            yield({"event": "response:delta", "data": delta})
                            full_response += delta
                    
                    if "type" in chunk and chunk["type"] == "message_stop":
                        yield({"event": "response:done_origin", "data": chunk})
                        yield({"event": "response:done", "data": full_response})
            else:
                # Generic streaming handler for other models
                async for chunk in response_generator:
                    yield({"event": "response:delta_origin", "data": chunk})
                    
                    if "amazon.titan" in self.default_options["modelId"]:
                        delta = chunk.get("outputText", "")
                    elif "meta.llama" in self.default_options["modelId"]:
                        delta = chunk.get("generation", "")
                    else:
                        delta = chunk.get("completion", "")
                        
                    if delta:
                        yield({"event": "response:delta", "data": delta})
                        full_response += delta
                
                yield({"event": "response:done", "data": full_response})

    def export(self):
        return {
            "generate_request_data": self.generate_request_data,
            "request_model": self.request_model,
            "broadcast_response": self.broadcast_response,
        }

def export():
    return ("Bedrock", Bedrock)