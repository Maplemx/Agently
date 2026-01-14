import asyncio
import json
from pathlib import Path
from typing import Any

from agently import Agently, TriggerFlow, TriggerFlowEventData
from agently.builtins.tools import Browse, Search

from .config import DEEPSEEK_API_KEY, SEARCH_PROXY


kb_collection = None


def _emit(data: TriggerFlowEventData, event_type: str, payload: Any):
    data.put_into_stream(json.dumps({"type": event_type, "data": payload}))


async def _build_kb_collection():
    try:
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
        collection = ChromaCollection(
            collection_name="agently_examples",
            embedding_agent=embedding,
        )
        docs = []
        for path in Path("examples").rglob("*.py"):
            content = path.read_text(encoding="utf-8")
            docs.append(
                {
                    "document": f"[FILE] {path}\n{content}",
                    "metadata": {"path": str(path)},
                }
            )
        if docs:
            collection.add(docs)
        return collection
    except Exception:
        return None


def build_flow() -> TriggerFlow:
    agent = Agently.create_agent()
    agent.set_settings(
        "OpenAICompatible",
        {
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "auth": DEEPSEEK_API_KEY,
            "options": {"temperature": 0.7},
        },
    )

    search = Search(
        proxy=SEARCH_PROXY,
        region="us-en",
        backend="google",
    )
    browse = Browse()

    tools_info = {
        "search": {
            "desc": "Search the web with {keywords}",
            "kwargs": {"keywords": [("str", "key word")]},
            "func": search.search,
        },
        "search_news": {
            "desc": "Search news with {keywords}",
            "kwargs": {"keywords": [("str", "key word")]},
            "func": search.search_news,
        },
        "browse": {
            "desc": "Browse the page at {url}",
            "kwargs": {"url": ("str", "Accessible URL")},
            "func": browse.browse,
        },
    }

    flow = TriggerFlow()

    async def start_request(data: TriggerFlowEventData):
        global kb_collection
        if kb_collection is None:
            _emit(data, "status", "kb preparing")
            kb_collection = await _build_kb_collection()
            if kb_collection is None:
                _emit(data, "status", "kb disabled")
            else:
                _emit(data, "status", "kb ready")
        return data.value

    async def prepare_context(data: TriggerFlowEventData):
        payload = data.value
        question = payload.get("question", "")
        chat_history = payload.get("chat_history", [])
        memo = payload.get("memo", [])
        agent.set_chat_history(chat_history)
        data.set_runtime_data("question", question)
        data.set_runtime_data("done_plans", [])
        data.set_runtime_data("step", 0)
        data.set_runtime_data("memo", memo)
        _emit(data, "status", "planning started")
        return question

    async def ensure_kb(data: TriggerFlowEventData):
        global kb_collection
        if kb_collection is None:
            kb_collection = await _build_kb_collection()
        if kb_collection is None:
            data.set_runtime_data("kb_results", [])
            return []
        results = kb_collection.query(data.get_runtime_data("question", ""))
        data.set_runtime_data("kb_results", results)
        return results

    async def make_next_plan(data: TriggerFlowEventData):
        question = data.get_runtime_data("question")
        done_plans = data.get_runtime_data("done_plans", [])
        step = data.get_runtime_data("step") or 0
        kb_results = data.get_runtime_data("kb_results") or []
        memo = data.get_runtime_data("memo") or []
        if step >= 5:
            final_action = {
                "type": "final",
                "reply": "Max steps reached. Please simplify your question and retry.",
            }
            await data.async_emit("Plan", final_action)
            return final_action

        tools_list = []
        for key, value in tools_info.items():
            tools_list.append(
                {
                    "tool_name": key,
                    "tool_desc": value["desc"],
                    "tool_args": value["kwargs"],
                }
            )

        request = (
            agent.input(question)
            .info({"tools": tools_list, "done": done_plans, "kb_results": kb_results, "memo": memo})
            .instruct(
                [
                    "Decide the next step based on {input}, {done}, and {tools}.",
                    "If {memo} contains constraints or preferences, follow them.",
                    "If an action keeps failing in {done}, choose 'final' and explain why.",
                    "If no tool is needed, choose 'final' and answer directly.",
                ]
            )
            .output(
                {
                    "next_step_thinking": ("str",),
                    "next_step_action": {
                        "type": ("'tool' | 'final'", "MUST IN values provided."),
                        "reply": ("str", "if type=='final' return the final answer, else ''"),
                        "tool_using": (
                            {
                                "tool_name": ("str from {tools.tool_name}", "Pick a tool from {tools}."),
                                "purpose": ("str", "Describe what you want to solve with the tool."),
                                "kwargs": ("dict", "Follow {tools.tool_args}."),
                            },
                            "if type=='tool' provide the tool plan, else null",
                        ),
                    },
                }
            )
        )
        response = request.get_response()
        thinking_started = False
        async for stream in response.get_async_generator(type="instant"):
            if stream.wildcard_path == "next_step_thinking" and stream.delta:
                if not thinking_started:
                    _emit(data, "thinking_delta", "")
                    thinking_started = True
                data.put_into_stream(json.dumps({"type": "thinking_delta", "data": stream.delta}))
            if stream.wildcard_path == "next_step_action.type" and stream.is_complete:
                _emit(data, "plan", {"next_action": stream.value})
            if stream.wildcard_path == "next_step_action.tool_using.tool_name" and stream.is_complete:
                _emit(data, "plan", {"tool": stream.value})
        result = response.result.get_data()
        next_action = result["next_step_action"]
        _emit(data, "status", "planning done")
        data.set_runtime_data("step", step + 1)
        await data.async_emit("Plan", next_action)
        return next_action

    async def use_tool(data: TriggerFlowEventData):
        tool_using_info = data.value["tool_using"]
        tool_name = tool_using_info["tool_name"].lower()
        tool = tools_info.get(tool_name)
        if tool is None:
            return {"type": "final", "reply": f"Unknown tool: {tool_name}"}

        _emit(data, "status", f"tool running: {tool_name}")
        tool_func = tool["func"]
        if asyncio.iscoroutinefunction(tool_func):
            tool_result = await tool_func(**tool_using_info["kwargs"])
        else:
            tool_result = tool_func(**tool_using_info["kwargs"])
        _emit(data, "status", f"tool done: {tool_name}")

        done_plans = data.get_runtime_data("done_plans", [])
        done_plans.append(
            {
                "purpose": tool_using_info["purpose"],
                "tool_name": tool_using_info["tool_name"],
                "result": tool_result,
            }
        )
        data.set_runtime_data("done_plans", done_plans)
        return {"type": "tool"}

    async def reply(data: TriggerFlowEventData):
        reply_text = data.value["reply"]
        _emit(data, "reply", reply_text)
        return reply_text

    async def update_memo(data: TriggerFlowEventData):
        memo = data.get_runtime_data("memo") or []
        question = data.get_runtime_data("question")
        reply_text = data.value.get("reply", "")
        result = (
            agent.input({"question": question, "reply": reply_text, "memo": memo})
            .instruct(
                [
                    "Extract any stable preferences, constraints, or facts to remember.",
                    "Only keep items that are useful for future turns.",
                    "Return an updated memo list.",
                ]
            )
            .output({"memo": [("str", "Short memo item")]})
            .start()
        )
        new_memo = result.get("memo", []) if isinstance(result, dict) else []
        if new_memo:
            _emit(data, "memo", new_memo)
        return {"type": "final", "reply": reply_text, "memo": new_memo}

    flow.to(start_request).to(prepare_context).to(ensure_kb).to(make_next_plan)
    (
        flow.when("Plan")
        .if_condition(lambda d: d.value.get("type") == "final")
        .to(reply)
        .to(update_memo)
        .else_condition()
        .to(use_tool)
        .to(make_next_plan)
        .end_condition()
    )

    return flow
