
import os
import requests
import re
import asyncio
import Agently
import json
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# 搜索工具
def search(keywords:list):
    payload = json.dumps({
        "q": ' '.join(keywords) if isinstance(keywords, list) else keywords,
    })
    headers = {
        'X-API-KEY': os.environ.get("SERPER_API_KEY"),
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", "https://google.serper.dev/search", headers=headers, data=payload)
    return response.text

# 浏览工具
def browse(url: str):
    content = ""
    try:
        request_options = {
            "headers": { "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36" }
        }
        page = requests.get(
            url,
            **request_options
        )
        soup = BeautifulSoup(page.content, "html.parser")
        # find text in p, list, pre (github code), td
        chunks = soup.find_all(["h1", "h2", "h3", "h4", "h5", "p", "pre", "td"])
        for chunk in chunks:
            if chunk.name.startswith("h"):
                content += "#" * int(chunk.name[-1]) + " " + chunk.get_text() + "\n"
            else:
                text = chunk.get_text()
                if text and text != "":
                    content += text + "\n"
        # find text in div that class=content
        divs = soup.find("div", class_="content")
        if divs:
            chunks_with_text = divs.find_all(text=True)
            for chunk in chunks_with_text:
                if isinstance(chunk, str) and chunk.strip():
                    content += chunk.strip() + "\n"
        content = re.sub(r"\n+", "\n", content)
        return content
    except Exception as e:
        return f"Can not browse '{ url }'.\tError: { str(e) }"

# 循环规划工具调用工作流定义
tool_using_workflow = Agently.Workflow()

@tool_using_workflow.chunk()
def save_user_input(inputs, storage):
    storage.set("user_input", inputs["default"])
    return

@tool_using_workflow.chunk()
def make_next_plan(inputs, storage):
    agent = storage.get("$agent")
    user_input = storage.get("user_input")
    tools_info = storage.get("tools_info", {})
    done_plans = storage.get("done_plans", [])
    tools_list = []
    for key, value in tools_info.items():
        tools_list.append({
            "工具名称": key,
            "工具描述": value["desc"],
            "所需参数": value["kwargs"],
        })
    result = (
        agent
            .input(user_input)
            .info({
                "可用工具清单": tools_list,
                "已经做过": done_plans,
            })
            .instruct([
                "根据{input}的用户意图，{已经做过}提供的行动记录以及{可用工具清单}提供的工具，制定解决问题的下一步计划",
                "如果{已经做过}提供的行动记录中，某项行动反复出现错误，可将下一步计划定为'输出结果'，回复内容为对错误的说明",
            ])
            .output({
                "next_step_thinking": ("str", ),
                "next_step_action": {
                    "type": ("'工具使用' | '输出结果'", "MUST IN values provided."),
                    "reply": ("str", "if {next_step_action.type} == '输出结果'，输出你的最终回复结果，else输出''"),                    
                    "tool_using": (
                        {
                            "tool_name": ("str from {可用工具清单.工具名称}", "必须使用{可用工具清单}提供的工具"),
                            "purpose": ("str", "描述使用工具希望解决的问题"),
                            "kwargs": ("dict，根据{可用工具清单.所需参数}要求给出所需参数"),
                        },
                        "if {next_step_action.type} == '工具使用'，给出你的工具使用计划说明，else输出null",
                    ),
                }
            })
            .start()
    )
    return result["next_step_action"]

@tool_using_workflow.chunk()
def reply(inputs, storage):
    if storage.get("print_process"):
        print("[💬 我觉得可以回复了]：")
        print("✅ 我得到的最终结果是：", inputs["default"]["reply"])
    return {
        "reply": inputs["default"]["reply"],
        "process_results": storage.get("done_plans"),
    }

@tool_using_workflow.chunk()
async def use_tool(inputs, storage):
    tool_using_info = inputs["default"]["tool_using"]
    tools_info = storage.get("tools_info")
    tool_func = tools_info[tool_using_info["tool_name"].lower()]["func"]
    if storage.get("print_process"):
        print("[🪛 我觉得需要使用工具]：")
        print("🤔 我想要解决的问题是：", tool_using_info["purpose"])
        print("🤔 我想要使用的工具是：", tool_using_info["tool_name"])
    if asyncio.iscoroutine(tool_func):
        tool_result = await tool_func(**tool_using_info["kwargs"])
    else:
        tool_result = tool_func(**tool_using_info["kwargs"])
    if storage.get("print_process"):
        print("🎉 我得到的结果是：", tool_result[:100], "...")
    done_plans = storage.get("done_plans", [])
    done_plans.append({
        "purpose": tool_using_info["purpose"],
        "tool_name": tool_using_info["tool_name"],
        "result": tool_result,
    })
    storage.set("done_plans", done_plans)
    return

(
    tool_using_workflow
        .connect_to("save_user_input")
        .connect_to("make_next_plan")
        .if_condition(lambda return_value, storage: return_value["type"] == "输出结果")
            .connect_to("reply")
            .connect_to("end")
        .else_condition()
            .connect_to("use_tool")
            .connect_to("make_next_plan")
)

# 附着到Agent之上
## 参考https://agently.tech/guides/model_settings/index.html切换到任意模型
search_agent = (
    Agently.create_agent()
        .set_settings("current_model", "OAIClient")
        #.set_settings("model.OAIClient.url", "https://api.deepseek.com/v1")
        #.set_settings("model.OAIClient.auth", { "api_key": os.environ.get("DEEPSEEK_API_KEY") })
        #.set_settings("model.OAIClient.options", { "model": "deepseek-chat" })
        .set_settings("model.OAIClient.url", "http://127.0.0.1:11434/v1")
        .set_settings("model.OAIClient.options", { "model": "deepseek-r1:14b" })
)
search_agent.attach_workflow("tool_using", tool_using_workflow)

# 使用新附着的tool_using方法，调用你提供的任意工具集回答问题
question = input("请输入您的问题：")
result = search_agent.tool_using(
    question,
    tools_info={
        "search": {
            "desc": "使用网络搜索工具，搜索{keywords}指定关键词相关信息",
            "kwargs": {
                "keywords": [("str", "key word")],
            },
            "func": search,
        },
        "browse": {
            "desc": "使用浏览工具，浏览{url}指定的页面内容",
            "kwargs": {
                "url": ("str", "可访问的URL地址")
            },
            "func": browse,
        },
    },
    print_process=True,
)
print("最终结果:\n", result["default"]["reply"])