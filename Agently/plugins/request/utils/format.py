def format_request_messages(request_messages, model_settings):
    system_prompt = ""
    system_messages = []
    chat_messages = []
    role_list = ["user", "assistant"]
    current_role = 0
    for message in request_messages:
        if message["role"] == "system":
            # no_multi_system_messages=True
            if model_settings.get_trace_back("message_rules.no_multi_system_messages"):
                if isinstance(message["content"], str):
                    system_prompt += f"{ message['content'] }\n"
                elif isinstance(message["content"], list):
                    for content in message["content"]:
                        if content["type"] == "text":
                            system_prompt += f"{ content['text'] }\n"
            # no_multi_system_messages=False
            else:
                system_messages.append(message)
        else:
            # strict_orders=True
            if model_settings.get_trace_back("message_rules.strict_orders"):
                if len(chat_messages) == 0 and message["role"] != "user":
                    chat_messages.append({ "role": "user", "content": [{"type": "text", "text": "What did we talked about?" }] })
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
    if model_settings.get_trace_back("message_rules.no_multi_system_messages") and system_prompt != "":
        system_messages.append({
            "role": "system",
            "content": [{
                "type": "text",
                "text": system_prompt
            }]
        })
    formatted_messages = system_messages.copy()
    formatted_messages.extend(chat_messages)
    # no_multi_type_messages=True
    if model_settings.get_trace_back("message_rules.no_multi_type_messages"):
        current_messages = formatted_messages.copy()
        formatted_messages = []
        for message in current_messages:
            if isinstance(message["content"], str):
                formatted_messages.append(message)
            elif isinstance(message["content"], list):
                for item in message["content"]:
                    if item["type"] == "text":
                        formatted_messages.append({ "role": message["role"], "content": item["text"] })
    return formatted_messages