from typing import Dict, Union
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    def __init__(self, server_params: Union[Dict, StdioServerParameters]=None):
        self._server_params = (
            server_params
            if isinstance(server_params, StdioServerParameters) or server_params is None
            else StdioServerParameters(**server_params)
        )
        self._exit_stack = AsyncExitStack()
        self._read = None
        self._write = None
        self._session = None
    
    async def __aenter__(self):
        await self.connect()
        return self.session
    
    async def __aexit__(self, _, __, ___):
        await self.close()

    async def connect(self, server_params: StdioServerParameters=None):
        server_params = server_params or self._server_params
        if not server_params:
            raise RuntimeError("MCP server parameters are required.")
        self._read, self._write = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self._session: ClientSession = await self._exit_stack.enter_async_context(ClientSession(self._read, self._write))
        await self._session.initialize()
    
    async def close(self):
        await self._exit_stack.aclose()

    @property
    def session(self):
        if not self._session:
            raise RuntimeError("Use .connect(<server_params>) to connect a MCP server first.")
        return self._session
    
    def _transform_schema_to_type(self, schema):
        if isinstance(schema, dict):
            # Handle `anyOf` / `oneOf`
            if 'anyOf' in schema or 'oneOf' in schema:
                key = 'anyOf' if 'anyOf' in schema else 'oneOf'
                return " | ".join(self._transform_schema_to_type(sub) for sub in schema[key])

            # Handle enums
            if 'enum' in schema:
                return " | ".join(f'"{v}"' for v in schema['enum'])

            # Handle const
            if 'const' in schema:
                val = schema['const']
                return f"{repr(val)}"

            # Handle type
            t = schema.get('type')
            if t == 'string':
                return "string"
            elif t == 'number' or t == 'integer':
                return "number"
            elif t == 'boolean':
                return "boolean"
            elif t == 'null':
                return "null"
            elif t == 'array':
                items = schema.get('items', {'type': 'any'})
                return f"Array<{self._transform_schema_to_type(items)}>"
            elif t == 'object':
                props = schema.get('properties', {})
                required = schema.get('required', [])
                parts = []
                for key, val in props.items():
                    optional = '?' if key not in required else ''
                    parts.append(f"{key}{optional}: {self._transform_schema_to_type(val)}")
                return f"{{{', '.join(parts)}}}"
            elif t == 'any':
                return "any"

        return "any"

    async def get_tools_info(self):
        tools = await self.session.list_tools()
        tools_info = []
        for tool in tools.tools:
            tools_info.append({
                "tool_name": tool.name,
                "desc": tool.description,
                "kwargs": {}
            })
            for key, value in tool.inputSchema["properties"].items():
                type = self._transform_schema_to_type(value)
                desc = (
                    value["description"]
                    if "description" in value
                    else (
                        value["desc"]
                        if "desc" in value
                        else None
                    )
                )
                tools_info[-1]["kwargs"].update({
                    key: (type, desc),
                })
        return tools_info
    
    async def call_tool(self, tool_name: str, kwargs: dict):
        response = await self.session.call_tool(tool_name, kwargs)
        return response.content[0].text