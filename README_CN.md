<img width="640" alt="image" src="https://github.com/user-attachments/assets/c645d031-c8b0-4dba-a515-9d7a4b0a6881" />

# Agently 4

[English Introduction](https://github.com/AgentEra/Agently/blob/main/README.md) | [中文介绍](https://github.com/AgentEra/Agently/blob/main/README_CN.md)

> *Speed Up Your GenAI Application Development*

[![license](https://img.shields.io/badge/证书-Apache2.0-blue.svg?style=flat-square)](https://github.com/AgentEra/Agently/blob/main/LICENSE)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/agently?style=flat-square)](https://pypistats.org/packages/agently)
[![GitHub star chart](https://img.shields.io/github/stars/agentera/agently?style=flat-square)](https://star-history.com/#agentera/agently)
[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/AgentlyTech.svg?style=social&label=Follow%20%40AgentlyTech)](https://x.com/AgentlyTech)
<a href="https://doc.weixin.qq.com/forms/AIoA8gcHAFMAScAhgZQABIlW6tV3l7QQf">
<img alt="WeChat" src="https://img.shields.io/badge/开发者交流微信群-申请加入-brightgreen?logo=wechat&style=flat-square">
</a>

<p>
  <a href="https://github.com/AgentEra/Agently/discussions/categories/general">
    <img alt="Discussions" src="https://img.shields.io/badge/交流讨论区-点击进入-brightgreen.svg?style=for-the-badge" />
  </a>
  <a href="https://github.com/AgentEra/Agently/discussions/categories/contribute-to-agently-4">
    <img alt="Contribute" src="https://img.shields.io/badge/成为贡献者-点击进入-blueviolet.svg?style=for-the-badge">
  </a>
  <a href="https://github.com/AgentEra/Agently/issues">
    <img alt="Issues" src="https://img.shields.io/badge/报告问题-点击报告-red.svg?style=for-the-badge">
  </a>
</p>

<hr />

<p align="center">
    <b><a href = "https://Agently.cn">💥 Agently官方网站</a> - 最详尽的Agently介绍文档&官方资讯</b>
</p>

<hr />

## 使用方法

Agently GenAI应用开发框架目前提供在Python语言中可用的包，开发者可以通过pip等包管理工具安装后，在代码中通过`from agently import Agently`的方式引入使用。

使用pip安装v4最新版本：

```shell
pip install -U agently
```

> ℹ️ 如果你想要寻找Agently v3版本的代码和文档，可以访问这个历史分支： [`v3-final`](https://github.com/AgentEra/Agently/tree/v3-final)


克隆本仓库安装：

```shell
git clone git@github.com:AgentEra/Agently.git
cd Agently
pip install -e .
```

## 文档与示例

- 文档站（中文）: https://Agently.cn/docs
- 适合循序渐进学习的代码样例：`examples/step_by_step/`

## 什么是Agently？

Agently GenAI应用开发框架希望为GenAI应用开发者带来易学、易用、高效的应用开发体验。以大型语言模型带来的技术突破和应用能力可能性为基础，并基于对GenAI应用在Runtime（运行时）对模型输出的控制要求的深度认知，在“模型输出层”-“业务应用层”之间，以开发框架的形式，为开发者提供灵活且恰当的抽象封装，帮助开发者屏蔽模型请求参数差异、表达格式差异、工程模块与模型/智能算法逻辑通讯的转换方式等繁琐细节，统一并简化业务表达方式；与此同时，不过度封装业务流程逻辑，给予GenAI应用开发者足够灵活的业务逻辑控制空间，以满足GenAI能力与现有系统能力无缝融合衔接的实际落地需要。

我们相信，GenAI能力是对于现有信息系统能力边界的重要扩展和不足，让现代信息系统过去的诸多不可能变为可能。而这些可能性都需要通过工程的方式，通过工程师、工具、工程思想让其变为现实，而不是过度强调GenAI的智能性和独立自主性，强行将GenAI应用和现有信息系统划分代际

因此，我们希望持续打造Agently GenAI应用开发框架及扩展套件，为所有GenAI应用开发者提供最重视开发者体验（Development Experience）的代码级开发解决方案。让每一个GenAI时代的开发者，都能够轻松、便利地将GenAI能力带入自己的应用之中。

## 从 Demo 到生产：Agently 在解决什么

在真实企业里，最难的往往不是“模型能不能回答”，而是系统能不能在真实流量、真实数据、真实依赖下稳定运行——能被测试、能被运维、能被持续迭代。Agently 4 的目标是把 LLM 的不确定性收进工程边界，让智能体从“灵感产品”变成“可靠系统”。

- **结构化输出（框架内置，和模型接口能力解耦）**：用 `output()` 定义契约，用 `ensure_keys` 兜住关键字段，并由框架在运行时完成解析/对齐/重试，不强依赖某些模型服务端的 `response_format/json_schema` 之类“专用开关”。这让你切换模型、切换推理服务时依然能保住接口契约。
- **工具调用规划 + 可追踪（不被 function calling 绑定）**：在 Agently 里，“要不要用工具、用哪个工具、参数怎么组装”是内置的规划步骤，不要求厂商接口必须支持 function calling / tool calling；每次执行都会在 `extra`（`tool_logs` / tool calls）里留下证据链，方便排障与审计。
- **TriggerFlow 可维护编排（低代码迁移到代码服务）**：把 n8n / Dify / Coze 这类可视化编排的“节点/连线/分支/汇聚/并发/循环”自然迁移为可评审、可测试、可持续维护的代码服务；配合 Instant 模式实时截取结构化节点 + 信号驱动触发，实现低代码难稳定表达的复杂实时编排。
- **知识库对齐与可溯源**：检索结果是结构化的（`id/document/metadata`），可以要求模型输出带 `source_id` + `quote` 的引用清单，让答案可审计、可复盘。

## 核心功能速览

这些“从 Demo 到生产”的典型难题，你大概率见过：
- **要 JSON，给你一段散文**：字段缺失、格式漂移、夹杂解释，解析链路一到线上就崩。
- **工具越接越多越难维护**：能跑，但复现不了；出错后只能“猜模型在想什么”。
- **低代码流程越画越乱**：最初很好用，后来分支/状态/复用/版本管理把团队拖住。
- **接了知识库仍然不敢用**：业务问“依据是哪段？”工程师答不上来，合规更不敢放行。

Agently 把这些问题收敛成可落地的工程能力：`output()` + `ensure_keys` 的契约化结构化输出、Instant 模式结构化流式消费、框架内置的工具规划与追踪、TriggerFlow 事件驱动编排，以及可溯源的知识库引用输出。

### 对大型语言模型流式输出、结构化输出的控制和消费

“先定契约，再生成”往往是智能体工程化的分水岭：你先把输出结构写清楚，框架在运行时把它变成稳定可解析的数据（并且不强依赖模型服务端是否支持 `response_format/json_schema`）。

使用Agently框架特别设计的，符合代码开发思维习惯的模型输出提示控制方案，能够让工程师拥有灵活而强大的模型输出控制能力：

```python
from agently import Agently

agent = Agently.create_agent()

(
    agent
        # 使用always参数，能够让这个部分的提示信息
        # 在本轮请求提交之后还会继续保留到之后的请求
        .input("What time is it now?", always=True)
        # 我们可以为任何模型提供一些工具说明的信息
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
        # 然后使用Agently风格的输出控制表达
        # 来让几乎任何模型都能做到Function Calling
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

根据上面设定好的输出要求，Agently框架允许开发者使用多种方式消费模型的输出结果：

```python
# 创建一个Response对象
# 这会将本次设置好的输出控制固化下来
# 接下来的所有新的设定将不会再影响这次response
response = agent.get_response()

# 获取模型的原始输出文本
response_text = response.get_text()

# 获取模型的解析后结果（结合output结构化控制使用）
response_data = response.get_data()
```

在真实应用中，我们更推荐 Instant 模式：在模型输出尚未完全结束的时候，就可以消费框架实时解析的结构化输出，并把“用户可见的文本”和“行为/指令”分发到不同模块（比如：对话窗口、函数调用、UI 动画/卡片、机器人动作控制器等）：

```python
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
        if instant_message.path == "tool_using_command.name" and instant_message.is_complete == True:
            print(f"I want to use: '{ instant_message.value }'")
        elif instant_message.path == "tool_using_command":
            print(f"call: { instant_message.value }")
            print(f"kwargs: { instant_message.value }")
```

```shell
I can check the current time for you. Please specify a timezone (e.g., 'America/New_York') so I can provide the accurate time.
[NO NEED TO USE TOOL!]
```

### 模型服务兼容（本地 / 云端 / 代理）

Agently 通过统一的 `OpenAICompatible` 配置屏蔽服务差异，并支持工程化常见配置（例如 `full_url`、自定义 headers 鉴权等）。

- 最小示例：
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

- 示例配置：`examples/model_configures/`
- Step-by-step：`examples/step_by_step/01-settings.py`

### 结构化输出稳定性（ensure_keys + 自动重试）

批量任务中，关键字段缺失会导致脚本失败。Agently 提供 `ensure_keys` + 自动重试，支持列表字段通配路径，适合工程落地的稳定性要求。

- 最小示例：
```python
from agently import Agently

agent = Agently.create_agent()
result = (
    agent.input("给我 3 个待办事项")
    .output({"todos": [("str", "todo item")]})
    .start(ensure_keys=["todos[*]"], max_retries=2, raise_ensure_failure=False)
)
print(result)
```
```text
运行结果（qwen2.5:7b）：
{'todos': ['购买超市购物清单上的所有物品', '与李经理确认项目截止日期', '整理办公室个人文件']}
```

- Step-by-step：`examples/step_by_step/03-output_format_control.py`

### 流式体验（delta / instant / typed_delta）

Agently 的流式输出面向真实应用：降低等待焦虑、提前暴露决策、按字段分发到不同 UI 区域。

比如在“陪伴机器人”的人机交互场景里，我们通常希望“说的话”和“动作/行为指令”混合生成，并且一旦解析到行为指令就立即执行，以提升交互的行动流畅度。

- 最小示例：
```python
from agently import Agently

agent = Agently.create_agent()
response = (
    agent.input("请扮演一个陪伴机器人：先向我打招呼，然后提出一个你接下来可以做的小动作。")
    .output(
        {
            "thinking": ("str", "内部规划（不展示给用户）"),
            "say": ("str", "给用户看的/听的内容"),
            "actions": [("str", "动作/行为指令（由应用层执行）")],
        }
    )
    .get_response()
)

say_label_printed = False

def execute_action(action: str) -> None:
    # 真实应用里，这里通常是发给机器人控制器 / UI 事件总线
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
```text
运行结果（qwen2.5:7b）：
[say] 您好！我是您的陪伴机器人，今天有什么可以帮到您的呢？我接下来可以给您讲一个笑话。
[action] 讲述笑话
```

- Step-by-step：`examples/step_by_step/06-streaming.py`
- 参考写法：`examples/basic/streaming_print.py`

### 工具调用（内置 + 自定义 + 可追踪）

当工具从 1 个增长到 20 个时，“昨天还能跑”远远不够：你需要可控的规划过程，以及能复盘、能审计的证据链（而不是被模型服务端 function calling 绑死）。

Tools 让模型可控地调用外部函数，并支持：
- 内置 `Search` / `Browse`
- 装饰器注册自定义工具
- 从 response 的 `extra` 里追踪 tool call

不同于依赖模型服务端 function calling 的方案，Agently 可以在普通 chat 接口上执行框架内置的“工具规划”步骤，让工具编排能力更容易跨模型迁移。

- 最小示例：
```python
from agently import Agently

agent = Agently.create_agent()

@agent.tool_func
def add(*, a: int, b: int) -> int:
    return a + b

agent.use_tools(add)
print(agent.input("用 add 工具计算 12 + 34").start())
```
```text
运行结果（qwen2.5:7b）：
执行加法操作: 46

使用 `add` 工具计算 \(12 + 34\) 的结果为 46。如果您需要进一步的数学帮助或有其他计算需求，欢迎继续提问！
```

- Step-by-step：`examples/step_by_step/07-tools.py`

### 工作流编排（TriggerFlow）

很多团队会先用 n8n / Dify / Coze 把流程跑通；真正的挑战发生在第二阶段：流程变复杂、要持续维护、要上线迭代。这时 TriggerFlow 把“节点/连线/分支/汇聚/并发/循环”自然翻译成可测试、可评审、可持续维护的代码服务。

TriggerFlow 是 Agently 的事件驱动编排引擎，支持：
- 分支（`when` / `if_condition` / `match`）
- 并发上限（`batch` / `for_each`）
- 循环（`emit` + `when`）
- 运行态流式事件（`put_into_stream`）

- 最小示例：
```python
from agently import TriggerFlow

flow = TriggerFlow()
flow.to(lambda d: f"Hello, {d.value}").end()
print(flow.start("Agently"))
```
```text
运行结果（qwen2.5:7b）：
Hello, Agently
```

- TriggerFlow 系列：`examples/step_by_step/11-triggerflow-01_basics.py`

### 知识库（embedding + 向量库）

在企业场景里，RAG 的关键问题往往不是“能不能检索到”，而是“答案是否对齐知识库、是否能给出可审计的引用来源”。

Agently 支持知识库接入（例如 Chroma）用于检索增强，并支持 metadata 追溯来源。

- 最小示例：
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
kb.add([{"document": "Agently 是一个 GenAI 应用开发框架。", "metadata": {"source": "demo"}}])
print(kb.query("Agently 是什么？"))
```

- Step-by-step：`examples/step_by_step/09-knowledge_base.py`

### 服务化（FastAPI + Docker）

仓库提供 docker-ready 的 FastAPI 工程，将 Auto Loop 以三种接口形式对外提供：
- SSE 流式
- WebSocket
- POST 请求

- 最小示例：
```shell
cd examples/step_by_step/13-auto_loop_fastapi
uvicorn app.main:app --reload
```

- 工程：`examples/step_by_step/13-auto_loop_fastapi/`

### 推荐学习路线（从零到能做项目）

建议按 step-by-step 顺序跑通：
- Settings → `examples/step_by_step/01-settings.py`
- Prompt 方法 → `examples/step_by_step/02-prompt_methods.py`
- 输出控制 → `examples/step_by_step/03-output_format_control.py`
- 流式输出 → `examples/step_by_step/06-streaming.py`
- Tools → `examples/step_by_step/07-tools.py`
- TriggerFlow → `examples/step_by_step/11-triggerflow-01_basics.py`
- Auto Loop → `examples/step_by_step/12-auto_loop.py`

## Agently Helper（桌面工具）

Agently Helper 是一个帮助你快速理解与测试 Agently 能力的桌面工具（无需先搭建完整工程）：
- 多模型管理与切换
- 不同 Prompt 方式间切换
- 结构化输出
- 流式输出

- Windows：https://1drv.ms/u/c/13d5207d1b13e4d3/IQC9XITZl83hR5vU9Z_t-0oKAd3jtMh_fYRypp7T2k8JhCY?e=I72GVH
- macOS（Apple 芯片）：https://1drv.ms/u/c/13d5207d1b13e4d3/IQBhdxYw9Ev1R6qTWb-esVK2AY8PwCxnBHLNuf06Ic4w7sw?e=unMjaD
- macOS（Intel 芯片）：https://1drv.ms/u/c/13d5207d1b13e4d3/IQDqUPSqRq7LR7gpCjK60FOSASl4PBsRZPGtHvBAA63U_js?e=EmwVMA
- Linux：https://1drv.ms/u/c/13d5207d1b13e4d3/IQDVenHvItjFTqnlv294MPD9AUQDvkAKwvBcNufEXSl1nAs?e=Ti5aJ7

## 💬 WeChat Group（加入微信群）

> [点击此处申请加入微信群](https://doc.weixin.qq.com/forms/AIoA8gcHAFMAScAhgZQABIlW6tV3l7QQf)
> 或扫描下方二维码：

<p align="center">
  <img width="120" alt="WeChat QR" src="https://github.com/AgentEra/Agently/assets/4413155/7f4bc9bf-a125-4a1e-a0a4-0170b718c1a6">
</p>
