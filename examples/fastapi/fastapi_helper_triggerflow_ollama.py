import os

from agently import Agently, TriggerFlow, TriggerFlowRuntimeData
from agently.integrations.fastapi import FastAPIHelper


OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
MODEL_NAME = "qwen2.5:7b"

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": OLLAMA_BASE_URL,
        "model": MODEL_NAME,
        "options": {
            "temperature": 0.3,
        },
    },
)

agent = Agently.create_agent()
agent.role("You are a concise and helpful assistant.", always=True)


def build_flow() -> TriggerFlow:
    flow = TriggerFlow()

    async def run_chat(data: TriggerFlowRuntimeData):
        payload = data.value if isinstance(data.value, dict) else {}
        if payload.get("raise_error"):
            raise RuntimeError("Demo runtime error from TriggerFlow provider.")
        user_input = str(payload.get("input", "")).strip()

        if not user_input:
            empty_reply = "Please provide input in payload.data.input."
            await data.async_put_into_stream({"event": "final", "content": empty_reply})
            await data.async_stop_stream()
            return {"input": user_input, "reply": empty_reply}

        response = agent.input(user_input).get_response()

        async for delta in response.get_async_generator(type="delta"):
            if delta:
                await data.async_put_into_stream({"event": "delta", "content": delta})

        final_reply = await response.async_get_text()
        await data.async_put_into_stream({"event": "final", "content": final_reply})
        await data.async_stop_stream()

        return {
            "input": user_input,
            "reply": final_reply,
        }

    flow.to(run_chat).end()
    return flow


flow = build_flow()

app = FastAPIHelper(
    response_provider=flow,
)

# You can use FastAPIHelper simple API creating methods
app.use_post("/flow/chat").use_get("/flow/chat/get").use_sse("/flow/chat/sse").use_websocket("/flow/chat/ws")


# You can also use `app` as a normal FastAPI application
@app.get("/health")
async def health():
    return {
        "ok": True,
        "provider": "triggerflow",
        "model": MODEL_NAME,
        "base_url": OLLAMA_BASE_URL,
    }


if __name__ == "__main__":
    import uvicorn

    print("Start FastAPIHelper TriggerFlow server on http://127.0.0.1:8001")
    print("POST payload format: {'data': {'input': 'hello'}, 'options': {}}")
    print("Error demo payload: {'data': {'input': 'hello', 'raise_error': True}, 'options': {}}")
    uvicorn.run(app, host="127.0.0.1", port=8001)
