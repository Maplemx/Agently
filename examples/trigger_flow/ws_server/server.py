import os
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from agently import Agently, TriggerFlow, TriggerFlowEventData
from agently.types.trigger_flow import RUNTIME_STREAM_STOP

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": os.environ["QIANFAN_BASE_URL"],
        "model": "ernie-lite-8k",
        "model_type": "chat",
        "auth": os.environ["QIANFAN_API_KEY"],
    },
)
Agently.set_settings("debug", True)

agent = Agently.create_agent()

app = FastAPI()

flow = TriggerFlow()


async def model_response(data: TriggerFlowEventData):
    response = (
        agent.set_chat_history(
            data.get_flow_data(
                "chat_history",
            )
        )
        .input(data.value)
        .get_response()
    )
    agen = response.get_async_generator("delta")
    async for delta in agen:
        data.put(("delta", delta))
    full_reply = await response.async_get_result()
    data.put(("final", full_reply))
    data.put(RUNTIME_STREAM_STOP)
    data.append_flow_data(
        "chat_history",
        {
            "role": "user",
            "content": data.value,
        },
        emit=False,
    )
    data.append_flow_data(
        "chat_history",
        {
            "role": "assistant",
            "content": full_reply,
        },
        emit=False,
    )
    return full_reply


flow.to(model_response).end()


@app.websocket("/")
async def trigger_flow_websocket(ws: WebSocket):
    await ws.accept()
    await ws.send_json(
        {
            "status": "received",
            "content": None,
            "stop": False,
        }
    )
    try:
        while True:
            data = await ws.receive_json()
            runtime_stream = flow.get_async_runtime_stream(data["user_input"], timeout=None)
            async for event, data in runtime_stream:
                if event == "delta":
                    await ws.send_json(
                        {
                            "status": "received",
                            "content": data,
                            "stop": False,
                        }
                    )
                elif event == "final":
                    await ws.send_json(
                        {
                            "status": "done",
                            "content": data,
                            "stop": True,
                        }
                    )
    except WebSocketDisconnect:
        pass
    except:
        await ws.close()
