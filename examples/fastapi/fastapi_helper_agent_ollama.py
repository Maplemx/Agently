import os

from agently import Agently
from agently.integrations.fastapi import FastAPIHelper


OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
MODEL_NAME = "qwen2.5:7b"

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": OLLAMA_BASE_URL,
        "model": MODEL_NAME,
        "request_options": {
            "temperature": 0.3,
        },
    },
)

agent = Agently.create_agent()
agent.role("You are a concise and helpful assistant.", always=True)

app = FastAPIHelper(
    response_provider=agent,
)

# You can use FastAPIHelper simple API creating methods
app.use_post("/agent/chat").use_get("/agent/chat/get").use_sse("/agent/chat/sse").use_websocket("/agent/chat/ws")


# You can also use `app` as a normal FastAPI application
@app.get("/health")
async def health():
    return {
        "ok": True,
        "provider": "agent",
        "model": MODEL_NAME,
        "base_url": OLLAMA_BASE_URL,
    }


if __name__ == "__main__":
    import uvicorn

    print("Start FastAPIHelper Agent server on http://127.0.0.1:8000")
    print("POST payload format: {'data': {'input': 'hello'}, 'options': {}}")
    uvicorn.run(app, host="127.0.0.1", port=8000)
