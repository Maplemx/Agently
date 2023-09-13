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
        llm_auth = runtime_ctx.get("llm_auth")
        llm_url = runtime_ctx.get("llm_url")
        core_agent.set_llm_name(llm_name)
        core_agent.set_llm_auth(llm_name, llm_auth[llm_name])
        if llm_url:
            core_agent.set_llm_url(llm_name, llm_url[llm_name])
        core_agent.set_proxy(runtime_ctx.get("proxy"))
        return

    blueprint\
        .manage_work_node("init_core_agent_auth")\
        .set_main_func(init_core_agent_auth)\
        .register()

    async def reply_with_prefer_judge(runtime_ctx, **kwargs):
        listener = kwargs["listener"]
        agent_runtime_ctx = kwargs["agent_runtime_ctx"]
        question = runtime_ctx.get("prompt_input")
        core_agent = runtime_ctx.get("core_agent")
        core_session = runtime_ctx.get("core_session")

        #Node 1: set user prefer
        user_prefer = agent_runtime_ctx.get("user_prefer")
        if user_prefer == None:
            user_prefer = []
        core_agent.set_role("user prefer", str(user_prefer))

        #Node 2: request with thinking
        result = core_session\
            .input(question)\
            .output({
                "reply": ("String",),
                "user_prefer": [("String", "过程中用户表现出的话题偏好，每个偏好不应超过2个单词")],
                "is_exit": ("Boolean", "用户想要结束对话并离开了吗？"),
                "is_close": ("Boolean", "本次对话之后，当前的对话话题还能继续聊下去吗？"),                
                "next_topic": ("String", "如果{{is_close}}为True,根据{{user_prefer}}可能衍生的话题，向用户提一个新的问题; 如果{{is_exit}}为True，首先对用户表示挽留，再向用户提一个daily life或有意思的故事或与{{user_prefer}}相关的问题，让用户有继续聊下去的欲望")
            })\
            .start()
        print("result", result)

        #Node 3: refill user prefer
        user_prefer = set(user_prefer)
        for tag in result["user_prefer"]:
            user_prefer.add(tag)
        user_prefer = list(user_prefer)
        agent_runtime_ctx.set("user_prefer", user_prefer)
        print("user prefer", agent_runtime_ctx.get("user_prefer"))

        #Node 4: feedback
        if result["is_exit"]:
            reply = result["next_topic"]
        elif result["is_close"]:
            reply = result["reply"] + '\n' + result["next_topic"]
        else:
            reply = result["reply"]
        await listener.emit("done", reply)

    blueprint\
        .manage_work_node("reply_with_prefer_judge")\
        .set_main_func(reply_with_prefer_judge)\
        .register()

    blueprint.set_workflow(["init_core_agent_auth","reply_with_prefer_judge"])

    return blueprint
