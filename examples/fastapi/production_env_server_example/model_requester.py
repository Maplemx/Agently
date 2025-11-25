import yaml
import json
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel
from agently import Agently
from typing import Literal

app = FastAPI()


class ModelRequestData(BaseModel):
    prompt: str | dict
    style: Literal["data", "yaml", "json", "text"] = "text"
    model: Literal["small", "large"] = "small"


@app.post("/request_model")
async def request_model(data: ModelRequestData):
    llm = Agently.create_agent()
    with open(Path(__file__).parent / "settings.yaml", encoding="utf-8") as file:
        settings = yaml.safe_load(file)
    model_mapping_name = data.model
    model_name = settings["model_mappings"][model_mapping_name]
    model_settings = settings["model_settings"][model_name]
    llm.set_settings("OpenAICompatible", model_settings)
    match data.style:
        case "yaml":
            if isinstance(data.prompt, dict):
                prompt = yaml.safe_dump(data.prompt)
            else:
                prompt = data.prompt
            llm.load_yaml_prompt(prompt)
        case "json" | "data":
            if isinstance(data.prompt, dict):
                prompt = json.dumps(data.prompt, ensure_ascii=False)
            else:
                prompt = data.prompt
            llm.load_json_prompt(prompt)
        case "text":
            llm.input(data.prompt)

    response = llm.get_response()

    try:
        return {
            "ok": True,
            "data": await response.async_get_data(),
            "text": await response.async_get_text(),
        }
    except Exception as e:
        return {
            "ok": False,
            "data": {},
            "text": str(e),
        }


if __name__ == "__main__":
    import uvicorn

    with open(Path(__file__).parent / "settings.yaml", encoding="utf-8") as file:
        settings = yaml.safe_load(file)

    uvicorn.run(app, host=settings["service_settings"]["host"], port=settings["service_settings"]["port"])
