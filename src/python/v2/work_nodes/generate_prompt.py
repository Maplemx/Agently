import yaml
import collections

from .generate_prompt_process import update_process

def ordered_dict_representer(dumper, data):
    return dumper.represent_dict(data.items())

yaml.add_representer(collections.OrderedDict, ordered_dict_representer)

def generate_prompt(runtime_ctx, **kwargs):
    process = kwargs["process"]
    '''
    SYSTEM MESSAGE
    '''
    system_prompt = collections.OrderedDict()
    #generate role
    role = runtime_ctx.get("agent_role")
    use_agent_role = runtime_ctx.get("use_agent_role")
    if role and use_agent_role:
        system_prompt["ROLE SETTINGS"] = {}
        for role_key, role_desc in role.items():
            system_prompt["ROLE SETTINGS"].update({ role_key : str(role_desc) })
    #generate status
    status = runtime_ctx.get("agent_status")
    use_agent_status = runtime_ctx.get("use_agent_status")
    if status and use_agent_status:
        system_prompt["STATUS"] = {}
        for status_key, status_desc in status.items():
            system_prompt["STATUS"].update({ status_key : str(status_desc) })
    if len(system_prompt) > 0:
        runtime_ctx.set("request_system_message", { "role": "system", "content": yaml.dump(system_prompt, allow_unicode=True) })
    '''
    REQUEST MESSAGE
    '''
    request_prompt_dict = collections.OrderedDict()
    prompt_input = runtime_ctx.get("prompt_input")
    prompt_instruct = runtime_ctx.get("prompt_instruct")
    prompt_segments = runtime_ctx.get("prompt_segments")
    prompt_output = runtime_ctx.get("prompt_output")
    prompt_output_format = runtime_ctx.get("prompt_output_format")
    prompt_style = runtime_ctx.get("prompt_style")
    if prompt_input != None and prompt_instruct == None and prompt_output == None:
        runtime_ctx.set("request_prompt_message", { "role": "user", "content": str(prompt_input) })
        if runtime_ctx.get("is_debug"):
            print("[PROMPT]")
            print(str(prompt_input))
    else:
        if prompt_input:
            request_prompt_dict["INPUT"] = prompt_input
        if prompt_instruct:
            request_prompt_dict["INSTRUCTIONS"] = prompt_instruct
        if prompt_segments:
            runtime_ctx.set("use_segments", True)
            pass#<-todo: segments
        elif prompt_output:
            prompt_output_format = prompt_output_format.upper() if prompt_output_format else ""
            if prompt_output_format not in process["generate_output_format"]:
                if isinstance(prompt_output, (dict, list)):
                    prompt_output_format = "JSON"
                    runtime_ctx.set("prompt_output_format", "JSON")
                else:
                    prompt_output_format = "TEXT"                
            request_prompt_dict["OUTPUT REQUIREMENT"] = process["generate_output_format"][prompt_output_format](prompt_output)
        request_prompt = process["generate_prompt_structure"][prompt_style](request_prompt_dict)
        if runtime_ctx.get("is_debug"):
            print("[PROMPT]")
            print(request_prompt)
        runtime_ctx.set("request_prompt_message", { "role": "user", "content": request_prompt})
    return

def export(agently):
    agently\
        .manage_work_node("generate_prompt")\
        .set_main_func(generate_prompt)\
        .set_runtime_ctx({
            "use_agent_role": {
                "layer": "agent",
                "alias": { "set": "use_role" }
            },
            "agent_role": {
                "layer": "agent",
                "alias": { "set_kv": "set_role" ,"append_kv": "append_role" },
            },
            "use_agent_status": {
                "layer": "agent",
                "alias": { "set": "use_status" }
            },
            "agent_status": {
                "layer": "agent",
                "alias": { "set_kv": "set_status", "append_kv": "append_status" },
            },
            "prompt_input": {
                "layer": "request",
                "alias": { "set": "input" },
            },
            "prompt_instruct": {
                "layer": "request",
                "alias": { "set_kv": "instruct" },
            },
            "prompt_output": {
                "layer": "request",
                "alias": { "set": "output" },
            },
            "prompt_segments": {
                "layer": "request",
                "alias": { "append": "segments" }
            },
        })\
        .register()
    update_process(agently.manage_work_node("generate_prompt"))
    return