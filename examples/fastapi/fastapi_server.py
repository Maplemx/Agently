import os
import dotenv

dotenv.load_dotenv(dotenv.find_dotenv())

from fastapi import FastAPI
from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": os.environ["QIANFAN_BASE_URL"],
        "model": "ernie-lite-8k",
        "model_type": "chat",
        "auth": os.environ["QIANFAN_API_KEY"],
    },
)

agent = Agently.create_agent()
agent.role("You are a helpful assistant", always=True)

app = FastAPI()


@app.get("/chat")
async def chat(user_input: str):
    return await agent.input(user_input).async_start()
