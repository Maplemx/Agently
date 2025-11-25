## Why to use?

Provide an RESTful API service that can use Agently model request enhance easily with Agently configure prompt expression format.

Developers can modify `settings.yaml` to switch models at runtime without stop and restart the service.

## How to use?

### Step 1. Install dependencies

Go into this example's folder and run `pip install -r requirements` command in shell.

### Step 2. Check and modify settings

Modify `settings.yaml` to suite your requirements.

```yaml
# Use model_mappings to state what model the value of parameter `model` actually point to.
model_mappings:
  small: qwen2.5-72b
  large: a800-ernie4.5-300b
# Use model_settings to provide model request configures for Agently OpenAICompatible model requester plugin.
# Visit https://github.com/AgentEra/Agently/tree/main/examples/model_configures to see model request configure examples.
model_settings:
  ernie4.5-300b:
    base_url: <Ernie4.5-300b-Base-URL>
    api_key: <api_key>
    model: en-45-turbo
  ernie4.5-21b:
    base_url: <Ernie4.5-21b-Base-URL>
    model: ernie45-21b-a3b
  qwen2.5-72b:
    base_url: <Qwen2.5-72b-Base-URL>
    api_key: <api_key>
    model: qwen25-ncq12f
# Use service_settings to state the host address and port of your service
service_settings:
  host: 0.0.0.0
  port: 15596
```

### Step 3. Start the service

Use Python to run `model_requester.py`.

### Step 4. Request API

Now you can request the API which URL like `http://localhost:15596/request_model` with `POST` method.

- httpx request example:

```python
import httpx

response = httpx.post(
    "http://localhost:15596/request_model",
    json={
        # Style you can use:
        # - data: accept structured dictionary prompt
        # - json: accept JSON string prompt
        # - yaml: accept YAML string prompt
        # - text: accept pure text prompt
        "style": "data",
        # Visit https://github.com/AgentEra/Agently/tree/main/examples/configure_prompt
        # to see examples about how to write Agently Configure Prompt Expression
        "prompt": {
            "input": "Who are you?",
            "output": {
                "thinking": {
                    "$type": "str",
                    "$desc": "Thinking about how will you reply",
                },
                "reply": {
                    "$type": "str",
                    "$desc": "Your final reply",
                }
            }
        },
        # Value of parameter 'model' is what you set to model_mappings
        # in settings.yaml from Step 2
        "model": "small",
    }
)
print(response.json())
```

- CURL command example:

```shell
curl -X POST "http://localhost:15596/request_model" \
  -H "Content-Type: application/json" \
  -d '{
    "style": "data",
    "prompt": {
      "input": "Who are you?",
      "output": {
        "thinking": {
          "$type": "str",
          "$desc": "Thinking about how will you reply"
        },
        "reply": {
          "$type": "str",
          "$desc": "Your final reply"
        }
      }
    },
    "model": "small"
  }'
```

and you will get response like this from the API:

```json
{
    "ok": true,
    "data": {
        "thinking": "OK, user asked me about who am I, I shall response politely.",
        "reply": "Hi, I am an AI assistant that can help you. Please ask me anything."
    },
    "text": "```json\n{\"thinking\": \"OK, user asked me about who am I, I shall response politely.\",\"reply\": \"Hi, I am an AI assistant that can help you. Please ask me anything.\"}```"
}
```

That means this service works. Have fun. ☕️