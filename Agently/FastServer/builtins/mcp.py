from typing import Union
from Agently.Agent import Agent
from Agently.Workflow import Workflow
from mcp.server import FastMCP

class MCPServerHandler:
    def serve_agent(self, agent: Agent, *, name:str=None, desc:str=None):
        if name is None or name == "":
            name = "Agently Agent"
        if desc is None or desc == "":
            desc = "Ask this agent anything for help."
        
        server = FastMCP(name)

        async def ask_agent(message:str):
            return agent.input(message).start()
        server.tool(
            name=name,
            description=desc,
        )(ask_agent)
        
        server.run()
    
    def serve_workflow(self, workflow: Workflow, *, name:str=None, desc:str=None):
        if name is None or name == "":
            name = "Agently Workflow"
        if desc is None or desc == "":
            desc = "A helpful workflow to solve any problem you submit."
        
        server = FastMCP(name)

        async def submit_to_workflow(message:str, initial_storage:dict=None):
            result = workflow.start(message, storage=initial_storage)
            return result["default"]
        submit_to_workflow.__doc__ = desc
        server.tool()(submit_to_workflow)

        server.run()
    
    def serve(self, target: Union[Agent, Workflow], *, name:str=None, desc:str=None):
        if isinstance(target, Agent):
            self.serve_agent(target, name=name, desc=desc)
        elif isinstance(target, Workflow):
            self.serve_workflow(target, name=name, desc=desc)
        else:
            raise TypeError(f"[Agently FastServer] Can not support target '{ target }'. Server target must be an Agently Agent or a Agently Workflow.")