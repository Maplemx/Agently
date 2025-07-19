import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from agently import Agently
from agently.utils import SettingsNamespace

Agently.set_debug_console("OFF")

request_settings = SettingsNamespace(
    Agently.settings,
    "plugins.ModelRequester.OpenAICompatible",
)
request_settings["base_url"] = os.environ["DEEPSEEK_BASE_URL"]
request_settings["model"] = os.environ["DEEPSEEK_DEFAULT_MODEL"]
request_settings["model_type"] = "chat"
request_settings["auth"] = os.environ["DEEPSEEK_API_KEY"]

request = Agently.create_request()
request.set_prompt("input", "Hello")
request.set_prompt(
    "output",
    {
        "thinking": ([(str,)], "Step by step"),
        "reply": (str, None, "Markdown Style"),
    },
)
result = request.get_result()
Agently.print(result)
