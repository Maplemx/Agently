import os
import dotenv
dotenv.load_dotenv(dotenv.find_dotenv())

import Agently

agent = (
    Agently.create_agent(is_debug=True)
        .set_settings("current_model", "OAIClient")
        # Use Ollama Local Model
        # .set_settings("model.OAIClient.url", "http://127.0.0.1:11434/v1")
        # .set_settings("model.OAIClient.options.model", "qwen2.5-coder:14b")
        # Or use DeepSeek API
        .set_settings("model.OAIClient.auth", { "api_key": os.environ.get("DEEPSEEK_API_KEY") })
        .set_settings("model.OAIClient.options", { "model": "deepseek-chat" })
        .set_settings("model.OAIClient.url", "https://api.deepseek.com/v1")
)

# 超简单调用各种MCP Server（包括你自己创建的Agent/工作流 MCP Server）
agent.use_mcp_server(
    command="python",
    args=["-u", "<Path/to/your/mcp/server>"],
    env=None,
).input("介绍一下长岛冰茶").start()

# agent.use_mcp_server(
#     command="python",
#     args=["-u", "<Path/to/your/mcp/server>"],
#     env=None,
# ).input("写一段求斐波那契数列第n位的代码").start()

# agent.use_mcp_server(
#     command="python",
#     args=["-u", "<Path/to/your/mcp/server>"],
#     env=None,
# ).input("今天旧金山天气怎么样").start()

# agent.use_mcp_server(
#     config={
#         "mcpServers": {
#             "weather_reporter": {
#                 "command": "python",
#                 "args": ["-u", "<Path/to/your/mcp/server>"]
#             },
#         },
#     }
# ).input("今天旧金山天气怎么样").start()