import yaml
import asyncio
from typing import Union, List
from datetime import datetime
from .utils import ComponentABC
from Agently.utils import RuntimeCtxNamespace, to_json_desc
from Agently.Workflow import Workflow
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ...Stage import Stage

from mcp.server.fastmcp import FastMCP

class Tool(ComponentABC):
    def __init__(self, agent: object):
        self._agent = agent
        self._is_debug = lambda: self._agent.settings.get_trace_back("is_debug")
        self._settings = RuntimeCtxNamespace("plugin_settings.agent_component.Tool", self._agent.settings)
        self._tool_manager = self._agent.tool_manager
        self._tools_info = {}
        self._tools_mapping = {}
        self._must_call_tools_info = None
        self._tool_using_workflow = self._get_default_tool_using_workflow()

    # put_event
    async def _put_event(self, event, data):
        await self._agent.call_event_listeners(event, data)
        self._agent.put_data_to_generator(event, data)

    # Normal Tool
    def register_tool(
        self,
        tool_name: str,
        desc: any,
        args: dict,
        func: callable,
        *,
        categories: Union[str, List[str]] = None,
    ):
        self._tool_manager.register(
            tool_name,
            desc,
            args,
            func,
            categories=categories,
        )
        self._tools_info.update({
            tool_name: {
                "tool_name": tool_name,
                "desc": desc,
                "kwargs": to_json_desc(args),
            }
        })
        return self._agent

    def remove_tools(self, tool_names: Union[str, List[str]]):
        if isinstance(tool_names, str):
            tool_names = [tool_names]
        for tool_name in tool_names:
            if tool_name in self._tools_info:
                del self._tools_info[tool_name]
        return self._agent
    
    def use_public_tools(self, tool_names: Union[str, List[str]]):
        if isinstance(tool_names, str):
            tool_names = [tool_names]
        for tool_name in tool_names:
            tool_info = self._tool_manager.get_tool_info(tool_name, with_args=True)
            if tool_info:
                self._tools_info.update({ tool_name: tool_info })
        return self._agent
    
    def use_public_categories(self, tool_categories: Union[str, List[str]]):
        if isinstance(tool_categories, str):
            tool_categories = [tool_categories]
        tools_info = self._tool_manager.get_tool_dict(categories=tool_categories, with_args=True)
        for key, value in tools_info.items():
            self._tools_info.update({ key: value })
        return self._agent

    def use_all_public_tools(self):
        tools_info = self._tool_manager.get_tool_dict(with_args=True)
        for key, value in tools_info.items():
            self._tools_info.update({ key: value })
        return self._agent
    
    # Must Call
    def must_call(self, tool_name: str):
        tool_info = self._tool_manager.get_tool_info(tool_name, with_args=True)
        if tool_info:
            self._must_call_tools_info = tool_info
        else:
            raise NotImplementedError(f"[Agent Component] Tool-must call: can not find tool named '{ tool_name }'.")
        return self._agent
    
    # MCP
    async def _get_tools_info_from_mcp_async(self, *, mcp_server_params: StdioServerParameters):
        async with stdio_client(mcp_server_params) as (read, write):
            async with ClientSession(read, write) as session:
                tools_info = {}
                await session.initialize()
                tools_data = await session.list_tools()
                for tool in tools_data.tools:
                    tools_info.update({
                        tool.name: {
                            "tool_name": tool.name,
                            "desc": tool.description,
                            "kwargs": {}
                        },
                    })
                    for key, value in tool.inputSchema["properties"].items():
                        desc_str = ""
                        if 'title' in value:
                            desc_str += f"{ value['title'] }\n"
                        if 'description' in value:
                            desc_str += f"{ value['description'] }"
                        tools_info[tool.name]["kwargs"].update({
                            key: (
                                value["type"],
                                desc_str,
                            ),
                        })
        return tools_info

    def _get_tools_info_from_mcp(self, *, mcp_server_params: StdioServerParameters):
        return asyncio.run(self._get_tools_info_from_mcp_async(mcp_server_params=mcp_server_params))

    def _generate_mcp_tool(self, mcp_server_params: StdioServerParameters, tool_name:str):
        async def _call_mcp_tool_async(**kwargs):
            async with stdio_client(mcp_server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await session.call_tool(tool_name, arguments=kwargs)
        def _call_mcp_tool(**kwargs):
            with Stage() as stage:
                result = stage.get(_call_mcp_tool_async, **kwargs)
                if result.isError:
                    return {
                        "Error": vars(result.content[0])
                    }
                else:
                    return vars(result.content[0])
        return _call_mcp_tool
    
    def use_mcp_server(
        self,
        command:str=None,
        args:List[str]=None,
        env:str=None,
        *,
        config:dict=None,
        categories:Union[str, List[str]]=None,
    ):
        if command and args:
            mcp_server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env,
            )
            tools_info = self._get_tools_info_from_mcp(mcp_server_params=mcp_server_params)
            for tool_name, tool_info in tools_info.items():
                self._tools_info.update({ tool_name: tool_info })
                self._tool_manager.register(
                    tool_info["tool_name"],
                    tool_info["desc"],
                    to_json_desc(tool_info["kwargs"]),
                    self._generate_mcp_tool(mcp_server_params, tool_info["tool_name"]),
                    categories=categories,          
                )
        elif config:
            if "mcpServers" in config:
                config = config["mcpServers"]
            for server_name, server_info in config.items():
                if "command" in server_info and "args" in server_info:
                    self.use_mcp_server(
                        command=server_info["command"],
                        args=server_info["args"],
                        env=server_info["env"] if "env" in server_info else None,
                        categories=categories,
                    )
        else:
            raise NotImplementedError(f"[Agent Component] Tool - Use MCP Server: `command`, `arg` or `config` dict must be provided.")
        return self._agent
    
    # Customize Workflow
    def set_tool_using_workflow(self, workflow: Workflow):
        self._tool_using_workflow = workflow
        return self._agent

    # Default Workflow
    def _get_default_tool_using_workflow(self):
        tool_using_workflow = Workflow()

        @tool_using_workflow.chunk()
        def save_user_input(inputs, storage):
            storage.set("user_input", inputs["default"])
            return

        @tool_using_workflow.chunk()
        async def make_next_plan(inputs, storage):
            agent = storage.get("$agent")
            user_input = storage.get("user_input", {})
            tools_info = storage.get("tools_info", {})
            done_plans = storage.get("done_plans", [])
            result = (
                agent
                    .input(user_input)
                    .info({
                        "tool_list": [to_json_desc(item) for item in list(tools_info.values())],
                        "already_dones": done_plans,
                        "now": datetime.now().strftime("%Y-%B-%d %H:%M:%S"),
                    })
                    .instruct([
                        "According {input}, {already_dones} and {HELPFUL INFORMATION.tool_list}, make a next move plan",
                        "If {already_dones} shows that some action repeats for too many times, next step MUST BE 'OUTPUT'",
                        "USE WHAT NATURAL LANGUAGE TONGUE {INPUT} USED AS POSSIBLE.",
                    ])
                    .output({
                        "input_natural_language": ("str", ),
                        "next_step_thinking": ("str", ),
                        "next_step_action": {
                            "type": ("'TOOL USING' | 'OUTPUT'", "MUST IN values provided. If {HELPFUL INFORMATION.already_dones} have enough info to reply {input}, MUST choose 'OUTPUT'"),
                            "tool_using": (
                                {
                                    "tool_name": ("str from {HELPFUL INFORMATION.tool_list.tool_name}", "MUST USE {HELPFUL INFORMATION.tool_list.tool_name} provided tool name ONLY!"),
                                    "purpose": ("str", "Describe the problem need to use this tool to solve"),
                                    "kwargs": ("dict", "MUST FOLLOW {HELPFUL INFORMATION.tool_list.kwargs} format requirement!"),
                                },
                                "if {next_step_action.type} == 'OUTPUT' just output null",
                            ),
                        }
                    })
                    .start()
            )
            await self._put_event("tool:planning", result["next_step_thinking"])
            return result["next_step_action"]

        @tool_using_workflow.chunk()
        async def use_tool(inputs, storage):
            tool_using_info = inputs["default"]["tool_using"]
            if storage.get("print_process"):
                print("[🤔 Need to use tool]: ")
                print("❓ Problem is:", tool_using_info["purpose"])
                print("🪛 Use tool:", tool_using_info["tool_name"])
            tool_result = self._tool_manager.call_tool_func(tool_using_info["tool_name"], **tool_using_info["kwargs"])
            if storage.get("print_process"):
                print("ℹ️ Tool result: ", tool_result[:100], "...")
            tool_using_result = {
                "purpose": tool_using_info["purpose"],
                "tool_name": tool_using_info["tool_name"],
                "result": tool_result,
            }
            done_plans = storage.get("done_plans", [])
            done_plans.append(tool_using_result)
            storage.set("done_plans", done_plans)
            await self._put_event("tool:tool_result", tool_using_result)
            return
    
        @tool_using_workflow.chunk()
        def reply(inputs, storage):
            if storage.get("print_process"):
                print("✅ Tool using Done!")
            return storage.get("done_plans", None)

        (
            tool_using_workflow
                .connect_to("save_user_input")
                .connect_to("make_next_plan")
                .if_condition(lambda return_value, storage: return_value["type"] == "OUTPUT")
                    .connect_to("reply")
                    .connect_to("end")
                .else_condition()
                    .connect_to("use_tool")
                    .connect_to("make_next_plan")
        )
        return tool_using_workflow
    
    async def _prefix(self):
        if self._must_call_tools_info:
            if self._is_debug():
                print(f"[Agent Component] Using Tools: Must call '{ self.must_call_tool_info['tool_name'] }'")
            self.agent.request.request_runtime_ctx.remove("prompt.instruct")
            self.agent.request.request_runtime_ctx.remove("prompt.output")
            return {
                "info": {
                    "function_must_call": {
                        "tool_name": self.must_call_tool_info["tool_name"],
                        "desc": self.must_call_tool_info["desc"],
                        "args": self.must_call_tool_info["args"],
                    },
                },
                "output": {
                    "can_call": ("Boolean", "Is all information especially from {input} above enough to generate all arguments in {function_must_call.args}?"),
                    "args": ("if {can_call} == true, generate args dict according {function_must_call.args} requirement, else leave argument value as null"),                    
                    "question": ("String", "if {can_call}==false, output question for user to collecting enough information."),
                }
            }
        elif len(self._tools_info.keys()) > 0:
            prompt = self._agent.request.request_runtime_ctx.get("prompt", {})
            if len(prompt.keys()) == 1 and "input" in prompt:
                prompt =  yaml.safe_dump(prompt["input"], allow_unicode=True)
            else:
                prompt = yaml.safe_dump(prompt, allow_unicode=True)
            tool_using_result = self._tool_using_workflow.start(
                prompt,
                storage={
                    "$agent": self._agent.worker_request,
                    "tools_info":self._tools_info,
                },
            )["default"]
            if tool_using_result and len(tool_using_result) > 0:
                await self._put_event("tool:done", tool_using_result)            
                return {
                    "info": {
                        "tool_using_result": tool_using_result,
                    },
                    "instruct": [
                        "MUST USE WHAT NATURAL LANGUAGE TONGUE {INPUT} USED TO OUTPUT!",
                        "Response according {tool_using_result}",
                        "summarize key points if possible.",                        
                        "Provide URL for keywords in markdown format if needed.",
                        "If error occurred or not enough information was given, response you don't know honestly unless you are very sure about the answer without information support.",
                    ]
                }
            else:
                return None
        else:
            return None
    
    def export(self):
        return {
            "prefix": self._prefix,
            "suffix": None,
            "alias": {
                "register_tool": { "func": self.register_tool },
                "call_tool": { "func": self._tool_manager.call_tool_func, "return_value": True },
                "set_tool_proxy": { "func": self._tool_manager.set_tool_proxy },
                "add_public_tools": { "func": self.use_public_tools },
                "use_public_tools": { "func": self.use_public_tools },
                "add_public_categories": { "func": self.use_public_categories },
                "use_public_categories": { "func": self.use_public_categories },
                "add_all_public_tools": { "func": self.use_all_public_tools },
                "use_all_public_tools": { "func": self.use_all_public_tools },
                "use_mcp_server": { "func": self.use_mcp_server },
                "set_tool_using_workflow": { "func": self.set_tool_using_workflow },
                "remove_tools": { "func": self.remove_tools },
                "must_call": { "func": self.must_call },
            }
        }

def export():
    return ("Tool", Tool)