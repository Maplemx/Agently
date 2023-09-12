import asyncio
import Agently

def get_blueprint():
    agently = Agently.create()
    blueprint = agently.create_blueprint()
    blueprint.set("agent_name", "SmartOne")
        
    core_agent = agently.create_agent()
    core_agent\
        .use_role(True)\
        .set_role("姓名", "SmartOne")\
        .use_context(True)

    core_session = core_agent.create_session()

    blueprint.set("core_agent", core_agent)
    blueprint.set("core_session", core_session)

    async def init_core_agent_auth(runtime_ctx, **kwargs):
        core_agent = runtime_ctx.get("core_agent")
        llm_name = runtime_ctx.get("llm_name")
        core_agent.set_llm_name(llm_name)
        core_agent.set_llm_auth(llm_name, runtime_ctx.get("llm_auth")[llm_name])
        core_agent.set_llm_url(llm_name, runtime_ctx.get("llm_url")[llm_name])
        core_agent.set_proxy(runtime_ctx.get("proxy"))
        return

    blueprint\
        .manage_work_node("init_core_agent_auth")\
        .set_main_func(init_core_agent_auth)\
        .register()

    async def reply_with_prefer_judge(runtime_ctx, **kwargs):
        listener = kwargs["listener"]
        agent_runtime_ctx = kwargs["agent_runtime_ctx"]
        question = runtime_ctx.get("question")
        core_agent = runtime_ctx.get("core_agent")
        core_session = runtime_ctx.get("core_session")
        user_prefer = agent_runtime_ctx.get("user_prefer")
        if user_prefer == None:
            user_prefer = []
        core_agent.set_role("user prefer", str(user_prefer))
        result = core_session\
            .input(question)\
            .output({
                "reply": ("String",),
                "user_prefer": [("String", "tag that you want to remember what user prefer.Must use 1 or 2 words per tag.")],
                "is_close": ("Boolean", "after reply is this topic over or not?"),
                "next_topic": ("String", "if {{is_close}} is True, reply a sentence to open next topic according")
            })\
            .start()
        #print("result", result)
        user_prefer = set(user_prefer)
        for tag in result["user_prefer"]:
            user_prefer.add(tag)
        user_prefer = list(user_prefer)
        agent_runtime_ctx.set("user_prefer", user_prefer)
        print("user prefer", agent_runtime_ctx.get("user_prefer"))
        reply = result["reply"]
        if result["is_close"]:
            reply += '\n' + result["next_topic"]
        await listener.emit("done", reply)

    blueprint\
        .manage_work_node("reply_with_prefer_judge")\
        .set_main_func(reply_with_prefer_judge)\
        .set_runtime_ctx({
            "question": {
                "layer": "request",
                "alias": { "set": "ask" },
            },
        })\
        .register()

    blueprint.set_workflow(["init_core_agent_auth","reply_with_prefer_judge"])

    return blueprint