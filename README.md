<img width="640" alt="image" src="https://github.com/user-attachments/assets/c645d031-c8b0-4dba-a515-9d7a4b0a6881" />

# Agently 4

[English Introduction](https://github.com/AgentEra/Agently/blob/main/README.md) | [中文介绍](https://github.com/AgentEra/Agently/blob/main/README_CN.md)


> *Speed Up Your GenAI Application Development*

[![license](https://img.shields.io/badge/license-Apache2.0-blue.svg?style=flat-square)](https://github.com/AgentEra/Agently/blob/main/LICENSE)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/agently?style=flat-square)](https://pypistats.org/packages/agently)
[![GitHub star chart](https://img.shields.io/github/stars/agentera/agently?style=flat-square)](https://star-history.com/#agentera/agently)
[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/AgentlyTech.svg?style=social&label=Follow%20%40AgentlyTech)](https://x.com/AgentlyTech)
<a href="https://doc.weixin.qq.com/forms/AIoA8gcHAFMAScAhgZQABIlW6tV3l7QQf">
<img alt="WeChat" src="https://img.shields.io/badge/WeChat%20Group-Apply-brightgreen?logo=wechat&style=flat-square">
</a>

<p>
  <a href="https://github.com/AgentEra/Agently/discussions/categories/general">
    <img alt="Discussions" src="https://img.shields.io/badge/Agently%20General%20Discussions-JOIN-brightgreen.svg?style=for-the-badge" />
  </a>
  <a href="https://github.com/AgentEra/Agently/discussions/categories/contribute-to-agently-4">
    <img alt="Contribute" src="https://img.shields.io/badge/Contribute%20to%20Agently%204%20-Join-blueviolet.svg?style=for-the-badge">
  </a>
  <a href="https://github.com/AgentEra/Agently/issues">
    <img alt="Issues" src="https://img.shields.io/badge/Report%20Issues-Report-red.svg?style=for-the-badge">
  </a>
</p>

<hr />

<p align="center">
    <b><a href = "https://github.com/AgentEra/Agently/discussions">💬 Official Github Discussion Forum</a> - Welcome to Share Anything about Agently with Us</b>
</p>

<hr />

## Getting Started

Agently is a Python-based framework for building GenAI applications. You can install it via pip and import features using `from agently import Agently`.

Install the latest version via pip:

```shell
pip install -U agently
```

> ℹ️ If you're looking for Agently v3's code and documents, please visit branch [`v3-final`](https://github.com/AgentEra/Agently/tree/v3-final)

Clone the repository and install locally:

```shell
git clone git@github.com:AgentEra/Agently.git
cd Agently
pip install -e .
```

## Documentation

- Docs (EN): https://agentera.github.io/Agently/en/
- 文档（中文）: https://agentera.github.io/Agently/zh/
- Step-by-step tutorials: `examples/step_by_step/`
- Auto Loop FastAPI (SSE/WS/POST, Docker-ready): `examples/step_by_step/13-auto_loop_fastapi/`

## What is Agently?

Agently aims to provide an intuitive, efficient, and developer-friendly framework for GenAI application development. By deeply understanding the runtime control needs of model outputs, Agently bridges the gap between large language models and real-world applications.

Agently abstracts away the complexities of:
- Varying model parameters
- Output formatting
- Communication between engineering modules and GenAI logic

...while giving developers full control over business logic and integration with existing systems.

We believe GenAI is not a generational replacement for current systems but a powerful extension. Engineers and tools are key to turning GenAI's possibilities into reality.

Our mission is to build the best developer experience (DX) for GenAI application engineers.

## Core Features Overview

### Structured and Streamed Output Control for LLMs

Agently allows you to control and consume model outputs using a developer-centric pattern:

```python
from agently import Agently

agent = Agently.create_agent()

(
    agent
        .input("What time is it now?", always=True)
        .info({
            "default_timezone": "",
            "tool_list": [{
                "name": "get_current_time",
                "desc": "Get current time by time zone provided",
                "kwargs": {
                    "timezone_str": (str, "time zone string in ZoneInfo()"),
                },
            }]
        })
        .output({
            "first_time_response": (str, ),
            "tool_using_judgement": (bool, ),
            "tool_using_command": (
                {
                    "name": (str, "Decide which tool to use by tool name:{tool_list.[].name}"),
                    "kwargs": (dict, "According {tool_list.[].args} to output kwargs dictionary"),
                },
                "If {tool_using_judgement}==False, just output {}",
            ),
        })
)
```

Then, consume the model response:

```python
response = agent.get_response()

# Get raw text
response_text = response.get_text()

# Get parsed structured data
response_data = response.get_data()

# Instant parsing mode (structured streaming)
instant_response_generator = response.get_generator(type="instant")

use_tool = False

for instant_message in instant_response_generator:
    if instant_message.path == "first_time_response":
        if instant_message.delta is not None:
            print(instant_message.delta, end="", flush=True)
    elif instant_message.path == "tool_using_judgement":
        use_tool = instant_message.value
        print()
        if use_tool:
            print("[USE TOOL!]")
        else:
            print("[NO NEED TO USE TOOL!]")
    if use_tool:
        if instant_message.path == "tool_using_command.name" and instant_message.is_complete:
            print(f"I want to use: '{ instant_message.value }'")
        elif instant_message.path == "tool_using_command":
            print(f"call: { instant_message.value }")
            print(f"kwargs: { instant_message.value }")
```

```shell
I can check the current time for you. Please specify a timezone (e.g., 'America/New_York') so I can provide the accurate time.
[NO NEED TO USE TOOL!]
```

### Provider Compatibility (Local / Hosted / Proxy)

Agently unifies model configuration via `OpenAICompatible`, so you can switch between providers while keeping the same developer experience. It also supports common “production reality” knobs like `full_url` and custom auth headers.

- Minimal example:
```python
from agently import Agently

Agently.set_settings(
    "OpenAICompatible",
    {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "auth": "DEEPSEEK_API_KEY",
    },
)
```

- Example configs: `examples/model_configures/`
- Step-by-step: `examples/step_by_step/01-settings.py`

### Output Reliability (ensure_keys + retries)

In batch tasks and pipelines, a missing field can crash the whole job. Agently provides `ensure_keys` + retries for structured output so you can enforce required fields (including wildcard paths for list items).

- Minimal example:
```python
from agently import Agently

agent = Agently.create_agent()
result = (
    agent.input("Give me 3 todos")
    .output({"todos": [("str", "todo item")]})
    .start(ensure_keys=["todos[*]"], max_retries=2, raise_ensure_failure=False)
)
print(result)
```

- Step-by-step: `examples/step_by_step/03-output_format_control.py`

### Streaming UX (delta / instant / typed_delta)

Agently streaming is designed for real applications: reduce waiting, expose decisions early, and route structured fields to different UI regions. For example in a “companion robot” HCI scenario, you often want to mix user-facing text with machine/behavior commands, and consume them as soon as they are parsed.

- Minimal example:
```python
from agently import Agently

agent = Agently.create_agent()
response = (
    agent.input("Act as a companion robot: greet me and propose a small action you can do next.")
    .output(
        {
            "thinking": ("str", "internal planning (not for users)"),
            "say": ("str", "what the user sees/hears"),
            "actions": [("str", "robot action command(s) for your app to execute")],
        }
    )
    .get_response()
)

say_label_printed = False

def execute_action(action: str) -> None:
    # In real apps, route this to your robot controller / UI event bus.
    print(f"\n[action] {action}")

for msg in response.get_generator(type="instant"):
    if msg.path == "say" and msg.delta:
        if not say_label_printed:
            print("[say] ", end="")
            say_label_printed = True
        print(msg.delta, end="", flush=True)
    if msg.path.startswith("actions[") and msg.is_complete:
        execute_action(msg.value)
print()
```

- Step-by-step: `examples/step_by_step/06-streaming.py`
- Reference patterns: `examples/basic/streaming_print.py`

### Tools (built-in + custom + traceable)

Tools let the model call external functions deterministically. Agently supports:\n- built-in `Search` / `Browse`\n- custom tools via decorator\n- tool call tracing from response metadata

- Minimal example:
```python
from agently import Agently

agent = Agently.create_agent()

@agent.tool_func
def add(*, a: int, b: int) -> int:
    return a + b

agent.use_tools(add)
print(agent.input("Use the add tool to calculate 12 + 34.").start())
```

- Step-by-step: `examples/step_by_step/07-tools.py`

### Workflow Orchestration (TriggerFlow)

TriggerFlow is Agently’s event-driven workflow engine, designed for:\n- branching (`when`, `if_condition`, `match`)\n- concurrency limits (`batch`, `for_each`)\n- loops (`emit` + `when`)\n- runtime stream events (`put_into_stream`)

- Minimal example:
```python
from agently import TriggerFlow

flow = TriggerFlow()
flow.to(lambda d: f"Hello, {d.value}").end()
print(flow.start("Agently"))
```

- TriggerFlow series: `examples/step_by_step/11-triggerflow-01_basics.py`

### Knowledge Base (embeddings + vector DB)

Agently integrates KB pipelines (e.g., Chroma) to ground responses with real documents and metadata.

- Minimal example:
```python
from agently import Agently
from agently.integrations.chromadb import ChromaCollection

embedding = Agently.create_agent()
embedding.set_settings(
    "OpenAICompatible",
    {
        "model": "qwen3-embedding:0.6b",
        "base_url": "http://127.0.0.1:11434/v1/",
        "auth": "nothing",
        "model_type": "embeddings",
    },
)
kb = ChromaCollection(collection_name="demo", embedding_agent=embedding)
kb.add([{"document": "Agently is a GenAI framework.", "metadata": {"source": "demo"}}])
print(kb.query("What is Agently?"))
```

- Step-by-step: `examples/step_by_step/09-knowledge_base.py`

### Deployment Templates (FastAPI, Docker)

For engineering delivery, the repo includes a docker-ready FastAPI project that exposes Auto Loop through:\n- SSE streaming\n- WebSocket\n- POST

- Minimal example:
```shell
cd examples/step_by_step/13-auto_loop_fastapi
uvicorn app.main:app --reload
```

- Project: `examples/step_by_step/13-auto_loop_fastapi/`

### Learn by Examples (Recommended Path)

Start with these step-by-step chapters (runnable code + explanations in docs):
- Settings → `examples/step_by_step/01-settings.py`
- Prompt Methods → `examples/step_by_step/02-prompt_methods.py`
- Output Control → `examples/step_by_step/03-output_format_control.py`
- Streaming → `examples/step_by_step/06-streaming.py`
- Tools → `examples/step_by_step/07-tools.py`
- TriggerFlow → `examples/step_by_step/11-triggerflow-01_basics.py`
- Auto Loop → `examples/step_by_step/12-auto_loop.py`

## Agently Helper (Desktop)

Agently Helper is a desktop tool to help you quickly **understand** and **test** Agently capabilities without setting up a full project first:
- Multi-model management and switching
- Switching between different prompt styles
- Structured output
- Streaming output

- Windows: https://1drv.ms/u/c/13d5207d1b13e4d3/IQC9XITZl83hR5vU9Z_t-0oKAd3jtMh_fYRypp7T2k8JhCY?e=I72GVH
- macOS (Apple Silicon): https://1drv.ms/u/c/13d5207d1b13e4d3/IQBhdxYw9Ev1R6qTWb-esVK2AY8PwCxnBHLNuf06Ic4w7sw?e=unMjaD
- macOS (Intel): https://1drv.ms/u/c/13d5207d1b13e4d3/IQDqUPSqRq7LR7gpCjK60FOSASl4PBsRZPGtHvBAA63U_js?e=EmwVMA
- Linux: https://1drv.ms/u/c/13d5207d1b13e4d3/IQDVenHvItjFTqnlv294MPD9AUQDvkAKwvBcNufEXSl1nAs?e=Ti5aJ7

## 💬 WeChat Group (Join Us)

> [Click Here to Apply](https://doc.weixin.qq.com/forms/AIoA8gcHAFMAScAhgZQABIlW6tV3l7QQf)
> or Scan the QR Code Below:

<p align="center">
  <img width="120" alt="WeChat QR" src="https://github.com/AgentEra/Agently/assets/4413155/7f4bc9bf-a125-4a1e-a0a4-0170b718c1a6">
</p>
