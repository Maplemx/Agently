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

# Get raw output
response_text = response.get_text()

# Get parsed structured result
response_dict = response.get_result()

# Streamed output
for delta in response.get_generator(content="delta"):
    print(delta, end="", flush=True)
```

Or use the instant parsing mode:

```python
instant_response_generator = response.get_generator(content="instant")

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

## [More documentation coming soon...]

## 💬 WeChat Group (Join Us)

> [Click Here to Apply](https://doc.weixin.qq.com/forms/AIoA8gcHAFMAScAhgZQABIlW6tV3l7QQf)
> or Scan the QR Code Below:

<p align="center">
  <img width="120" alt="WeChat QR" src="https://github.com/AgentEra/Agently/assets/4413155/7f4bc9bf-a125-4a1e-a0a4-0170b718c1a6">
</p>