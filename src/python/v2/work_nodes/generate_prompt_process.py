'''
TEXT
'''
def generate_output_format_text(prompt_output):
    return prompt_output

'''
JSON
'''
def transform_to_json_desc(origin, layer_count=0):
    if isinstance(origin, dict):
        json_string = ""
        if layer_count > 0:
            json_string += "\n"
        json_string += ("\t" * layer_count) + "{\n"
        for key, value in origin.items():
            json_string += ("\t" * (layer_count + 1)) + "\"" + key + "\": " + transform_to_json_desc(value, layer_count + 1) + "\n"
        if layer_count > 0:
            json_string += ("\t" * (layer_count + 1)) + "},"
        else:
            json_string += "}"
        return json_string
    elif isinstance(origin, list):
        json_string = ""
        if layer_count > 0:
            json_string += "\n"
        json_string += ("\t" * layer_count) + "[\n"
        for item in origin:
            json_string += ("\t" * (layer_count + 1)) + transform_to_json_desc(item, layer_count + 1) + ",\n"
        json_string += ("\t" * (layer_count + 1)) + "...\n"
        if layer_count > 0:
            json_string += ("\t" * layer_count) + "],"
        else:
            json_string += "]"
        return json_string
    elif isinstance(origin, tuple):
        json_string = f"<{ origin[0] }>,"
        if len(origin) >= 2:
            json_string += f"//{ origin[1] }"
        return json_string
    else:
        return str(origin)

def generate_output_format_json(prompt_output):
    return {
        "TYPE": "JSON String can be parsed in Python",
        "FORMAT": transform_to_json_desc(prompt_output, 0)
    }

'''
YAML
'''
def transform_to_yaml_desc(origin, layer_count=0):
    if isinstance(origin, dict):
        yaml_string = ""
        yaml_string += "  " * layer_count
        for key, value in origin.items():
            yaml_string += key + ": " + transform_to_yaml_desc(value, layer_count + 1) + "\n"
        return yaml_string
    elif isinstance(origin, list):
        yaml_string = ""
        if layer_count > 0:
            yaml_string += "\n"
        for item in origin:
            yaml_string += ("  " * (layer_count)) + "- " + transform_to_yaml_desc(item, layer_count) + "\n"
        yaml_string += ("  " * (layer_count)) + "- ...\n"
        return yaml_string
    elif isinstance(origin, tuple):
        yaml_string = f"<{ origin[0] }>"
        if len(origin) >= 2:
            yaml_string += f" #{ origin[1] }"
        return yaml_string
    else:
        return str(origin)

def generate_output_format_yaml(prompt_output):
    return {
        "TYPE": "YAML, allow_unicode=True, can be parsed in Python by yaml.safe_load() without explanation and decoration.",
        "FORMAT": "```yaml\n" + transform_to_yaml_desc(prompt_output, 0) + "```\n",
        "DOUBLE CHECK": "Make sure every key {{FORMAT}} required is in {{OUTPUT}}"
    }

'''
PROMPT Structure
'''
def generate_prompt_structure_default(request_prompt_dict, layer_count = 1):
    request_prompt = ""
    for key, content in request_prompt_dict.items():
        request_prompt += f"{ '#' * layer_count } { key }:\n"
        if isinstance(content, dict):
            request_prompt += generate_prompt_structure_default(content, layer_count + 1) + '\n'
        else:
            request_prompt += str(content) + '\n'
        if layer_count == 1:
            request_prompt += "\n"
    if layer_count == 1:
        request_prompt += "# OUTPUT:\n"
    return request_prompt

def update_process(work_node_management):
    result = work_node_management\
        .set_process("generate_output_format", generate_output_format_json, "JSON")\
        .set_process("generate_output_format", generate_output_format_yaml, "YAML")\
        .set_process("generate_output_format", generate_output_format_text, "TEXT")\
        .set_process("generate_prompt_structure", generate_prompt_structure_default, "default")\
        .set_runtime_ctx({
            "prompt_output_format": {
                "layer": "request",
                "alias": { "set": "format" },
                "default": "customize",
            },
            "prompt_style": {
                "layer": "session",
                "alias": { "set": "style" },
                "default": "default",
            },
        })\
        .update()
    return