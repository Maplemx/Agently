import asyncio
import json
import yaml
import re

async def loads_and_fix(content, output_format, fix_count=0, worker_agent=None, is_debug=False):
    fix_count += 1
    match = re.match(r"^```(.*)\n", content)
    if match:
        prefix = match.group(0)
        content = content.replace(prefix, "")
        content = content.replace("```", "")
    if output_format.upper() not in ("JSON", "YAML"):
        return content
    if worker_agent:
        async def fix_yaml_format(content, e):
            if is_debug:
                print('[Worker Agent Activated]')
                print('Fix YAML Format Error:', e)
                print('Current Ouput: ', content)
                print('\n')
            fixed_content = await worker_agent\
                .input({
                    "origin YAML String": content,
                    "error": e,
                })\
                .output('Fixed YAML String only without explanation and decoration.')\
                .async_start()
            if is_debug:
                print('Fixed Content:', fixed_content)
                print('\n')
            return fixed_content

        if fix_count >= 3:
            raise Exception(f'Format Error can not be fixed: [{ output_format }]\n{ content }')
        try:
            if output_format.upper() == "JSON":
                content = json.loads(content)
                return content
            elif output_format.upper() == "YAML":
                content = yaml.safe_load(content)
                prompt_output = runtime_ctx.get("prompt_output")
                if len(content.keys()) < len(prompt_output.keys()):
                    if is_debug:
                        print('[Worker Agent Activated]')
                        print('Fix YAML Format Error: Not enough output keys.')
                        print('Output requirement: ', str(runtime_ctx.get("prompt_output")))
                        print('Current Output: ', content)
                        print('\n')
                    fixed_content = await worker_agent\
                        .input({
                            "output keys requirement": str(runtime_ctx.get("prompt_output")),
                            "current output": content
                        })\
                        .output('Fixed YAML FORMAT STRING ONLY without explanation and decoration.')\
                        .async_start()
                    if is_debug:
                        print('Fixed Content:', fixed_content)
                        print('\n')
                    return await loads_and_fix(fixed_content, output_format, fix_count)
                else:
                    return content
        except json.JSONDecodeError as e:
            if is_debug:
                print('[Worker Agent Activated]')
                print('Fix JSON Format Error:', e.msg)
                print('Current Ouput: ', content)
                print('\n')
            fixed_content = await worker_agent\
                .input({
                    "origin JSON String": content,
                    "error": e.msg,
                    "position": e.pos,
                })\
                .output('Fixed JSON String only without explanation and decoration.')\
                .async_start()
            if is_debug:
                print('Fixed Content:', fixed_content)
                print('\n')
            return await loads_and_fix(fixed_content, output_format, fix_count=fix_count, worker_agent=worker_agent, is_debug=is_debug)
        except yaml.scanner.ScannerError as e:
            fixed_content = await fix_yaml_format(content, e)
            return await loads_and_fix(fixed_content, output_format, fix_count=fix_count, worker_agent=worker_agent, is_debug=is_debug)
        except yaml.parser.ParserError as e:
            fixed_content = await fix_yaml_format(fixed_content, e)
            return await loads_and_fix(fixed_content, output_format, fix_count=fix_count, worker_agent=worker_agent, is_debug=is_debug)
    else:
        if output_format.upper() == "JSON":
            return json.loads(content)
        if output_format.upper() == "YAML":
            return yaml.safe_load(content)