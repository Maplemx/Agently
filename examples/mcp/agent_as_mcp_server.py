# 超快速把你的Agent创建为MCP Server
import Agently

fast_server = Agently.FastServer(type="mcp")

agent = (
    Agently.create_agent(is_debug=True)
         .set_settings("current_model", "OAIClient")
         .set_settings("model.OAIClient.url", "http://127.0.0.1:11434/v1")
         .set_settings("model.OAIClient.options.model", "qwen2.5-coder:14b")
)

agent.set_agent_prompt("role", "你是编程专家")
agent.set_agent_prompt("instruct", "你必须用中文输出")
agent.use_mcp_server(
    command="python",
    args=["-u", "/Users/moxin/Library/Mobile Documents/com~apple~CloudDocs/projects/live/Agently_and_MCP/cocktail_server.py"],
    env=None,
)

fast_server.serve(
    agent,
    name="coder",
    desc="Ask any question about code or ask him to write a part of code for you."
)