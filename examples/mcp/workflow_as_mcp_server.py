# 超快速把你制作的智能工作流创建为MCP Server
import Agently

workflow = Agently.Workflow()

@workflow.chunk()
def get_weather(inputs, storage):
    return {
        "temperature": 24,
        "general": "sunny",
        "windy": 2,
        "wet": 0.3,
    }

(
    workflow
        .connect_to("get_weather")
        .connect_to("END")
)

fast_server = Agently.FastServer("mcp")

fast_server.serve(
    workflow,
    name="weather_reporter",
    desc="Get weather by submit city name to `message`"
)