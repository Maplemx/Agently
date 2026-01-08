import asyncio
from pathlib import Path

from agently import Agently, TriggerFlow, TriggerFlowEventData
from agently.builtins.tools import Browse, Search


## Auto Loop: plan -> tool -> plan -> reply (TriggerFlow + chat history + KB)
def auto_loop_demo():
    # Idea: a planning loop that keeps asking/using tools until ready to reply,
    # then continues with the next user turn.
    # Flow: input -> plan -> tool -> plan -> reply -> loop
    # Expect: prints a readable "plan/tool/result" process and final replies.
    agent = Agently.create_agent()
    import os
    import dotenv

    dotenv.load_dotenv(dotenv.find_dotenv())
    agent.set_settings(
        "OpenAICompatible",
        {
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "auth": os.environ.get("DEEPSEEK_API_KEY"),
            "options": {
                "temperature": 0.7,
            },
        },
    )

    # Built-in tools (Search/Browse). Configure proxy if needed.
    search = Search(
        proxy="http://127.0.0.1:55758",
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
    kb_collection = None

    async def start_loop(data: TriggerFlowEventData):
        nonlocal kb_collection
        if kb_collection is None:
            print("[📚] Preparing knowledge base from examples...")
            kb_collection = await build_kb_collection()
            if kb_collection is None:
                print("[📚] Knowledge base disabled (init failed).")
            else:
                print("[📚] Knowledge base ready.")
        await data.async_emit("Loop", None)
        return None

    async def get_input(data: TriggerFlowEventData):
        try:
            question = input("Question (type 'exit' to stop): ").strip()
        except EOFError:
            question = "exit"
        if question.lower() == "exit":
            data.stop_stream()
            return "exit"
        await data.async_emit("UserInput", question)
        return question

    async def prepare_context(data: TriggerFlowEventData):
        question = data.value
        chat_history = data.get_runtime_data("chat_history") or []
        agent.set_chat_history(chat_history)
        data.set_runtime_data("question", question)
        data.set_runtime_data("done_plans", [])
        data.set_runtime_data("step", 0)
        data.set_runtime_data("print_process", True)
        if data.get_runtime_data("memo") is None:
            data.set_runtime_data("memo", [])
        data.put_into_stream("[status] planning started\n")
        return question

    async def ensure_kb(data: TriggerFlowEventData):
        # Build a knowledge base from all example files once per process.
        nonlocal kb_collection
        if kb_collection is None:
            kb_collection = await build_kb_collection()

        if kb_collection is None:
            data.set_runtime_data("kb_results", [])
            return []
        results = kb_collection.query(data.get_runtime_data("question", ""))
        data.set_runtime_data("kb_results", results)
        return results

    async def build_kb_collection():
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
            .info(
                {
                    "tools": tools_list,
                    "done": done_plans,
                    "kb_results": kb_results,
                    "memo": memo,
                }
            )
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
        next_action = None
        thinking_started = False
        async for stream in response.get_async_generator(type="instant"):
            if stream.wildcard_path == "next_step_thinking" and stream.delta:
                if not thinking_started:
                    data.put_into_stream("[thinking] ")
                    thinking_started = True
                data.put_into_stream(stream.delta)
            if stream.wildcard_path == "next_step_thinking" and stream.is_complete:
                data.put_into_stream("\n")
            if stream.wildcard_path == "next_step_action.type" and stream.is_complete:
                data.put_into_stream(f"[plan] next_action: {stream.value}\n")
            if stream.wildcard_path == "next_step_action.tool_using.tool_name" and stream.is_complete:
                data.put_into_stream(f"[plan] tool: {stream.value}\n")
        result = response.result.get_data()
        next_action = result["next_step_action"]
        data.put_into_stream("[status] planning done\n")
        data.set_runtime_data("step", step + 1)
        await data.async_emit("Plan", next_action)
        return next_action

    async def use_tool(data: TriggerFlowEventData):
        tool_using_info = data.value["tool_using"]
        tool_name = tool_using_info["tool_name"].lower()
        tool = tools_info.get(tool_name)
        if tool is None:
            return {"type": "final", "reply": f"Unknown tool: {tool_name}"}

        data.put_into_stream(f"[status] tool running: {tool_name}\n")
        if data.get_runtime_data("print_process"):
            print("[🪛 I should use a tool]")
            print("🤔 Purpose:", tool_using_info["purpose"])
            print("🤔 Tool:", tool_using_info["tool_name"])

        tool_func = tool["func"]
        if asyncio.iscoroutinefunction(tool_func):
            tool_result = await tool_func(**tool_using_info["kwargs"])
        else:
            tool_result = tool_func(**tool_using_info["kwargs"])

        if data.get_runtime_data("print_process"):
            print("🎉 Result:", str(tool_result)[:200], "...")
        data.put_into_stream(f"[status] tool done: {tool_name}\n")

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
        if data.get_runtime_data("print_process"):
            print("[💬 Ready to answer]")
            print("✅ Final answer:", reply_text)
        data.put_into_stream("[status] reply ready\n")
        chat_history = data.get_runtime_data("chat_history") or []
        question = data.get_runtime_data("question")
        chat_history.append({"role": "user", "content": question})
        chat_history.append({"role": "assistant", "content": reply_text})
        data.set_runtime_data("chat_history", chat_history)
        await data.async_emit("Loop", None)
        return reply_text

    async def update_memo(data: TriggerFlowEventData):
        # Keep a runtime memo across turns for preferences, constraints, or facts.
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
            .output({"memo": [(str, "Short memo item")]})
            .start()
        )
        new_memo = result.get("memo", []) if isinstance(result, dict) else []
        if new_memo:
            data.set_runtime_data("memo", new_memo)
            data.put_into_stream(f"[memo] {new_memo}\n")
        return {"type": "final", "reply": reply_text}

    flow.to(start_loop)
    flow.when("Loop").to(get_input)
    flow.when("UserInput").to(prepare_context).to(ensure_kb).to(make_next_plan)
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

    for event in flow.get_runtime_stream("start", timeout=None):
        print(event, end="", flush=True)

    return flow


# auto_loop_demo()
