'''
Quick Start with a Worker Agent
'''

import Agently
import asyncio
import json

worker = Agently.create_worker()

#worker.set("is_debug", True)

worker.set_llm_auth("GPT", "Your-API-Key")

#Let's start with a simple one:
def quick_start():
    result = worker\
        .input("Give me 5 words and 1 sentence.")\
        .output({
            "words": ("Array",),
            "sentence": ("String",),
        })\
        .start()
    print(result)
    print(result["words"][2])
    return

#quick_start()

#Let the worker try to fix broken json string for you:
#(tip: don't forget `import json`)
def fix_json(json_string, round_count = 0):
    round_count += 1
    try:
        json.loads(json_string)
        return json_string
    except json.JSONDecodeError as e:
        print("[Worker Agent Activated]: Round", round_count)
        print("Fix JSON Format Error:\n", e.msg)
        print("Origin String:\n", json_string, "\n")
        fixed_result = worker\
            .input({
                "origin JSON String": json_string,
                "error": e.msg,
                "position": e.pos,
            })\
            .output("Fixed JSON String only without explanation and decoration.")\
            .start()
        print("Fixed Content:\n", fixed_result, "\n")
        return fix_json(fixed_result, round_count)

#result = fix_json("{'words': ['apple', 'banana', 'carrot', 'dog', 'elephant'], 'sentence': 'I have an apple, a banana, a carrot, a dog, and an elephant.'}")
#print(result)

#Let the worker try to call a function from natural language command
#First we designed a dict to storage tools' info for worker agent
#and callable functions are put in the dict too.
tools = {
    "weather_report": {
        "desc": "get weather report for the present time",
        "input_requirement": {
            "location": ("String", "your location")
        },
        "func": lambda **kwargs: print("The weather is sunny right now.\n", kwargs)
    },
    "weather_forecast": {
        "desc": "get weather forecast for the next 2-24 hours.",
        "input_requirement": {
            "location": ("String", "your location"),
        },
        "func": lambda **kwargs: print("There'll be raining 3 hours later.\n", kwargs)
    },
    "file_browser": {
        "desc": "Browse files that are given to.",
        "input_requirement": {
            "file_path": ("String", "File path that to be browsed."),
            "chunk_num": ("Number", "How many chunks to be output?"),
            "need_summarize": ("Boolean", "Do user need a summarize about the file?")
        },
        "func": lambda **kwargs: print("File browse work done.\n", kwargs)
    },
}

# Then let the worker agent to decide when and how to call the tools
def call_tools(natural_language_input):
    #step 1. confirm tools to be used
    tools_desc = []
    for tool_name, tool_info in tools.items():
        tools_desc.append({ "name": tool_name, "desc": tool_info["desc"] })
    tools_to_be_used = worker\
        .input({
            "input": natural_language_input,
            "tools": str(tools_desc)
        })\
        .output([("String", "Tool name in {{input.tools}} to response {{input}}'s requirement.")])\
        .start()
    #step 2. genrate parameters and call tools
    for tool_name in tools_to_be_used:
        call_parameters = worker\
            .input({
                "input": natural_language_input,
            })\
            .output(tools[tool_name]["input_requirement"])\
            .start()
        tools[tool_name]["func"](**call_parameters)
#call_tools("Browse ./readme.pdf for me and chunk to 3 pieces without summarize and check Beijing's next 24 hours weather for me.")

# Because of worker agent DID NOT HAVE context manage work node in workflow
# Let's create a normal agent
my_agently = Agently.create()
my_agent = my_agently.create_agent()

# Set authorization, of course
my_agent.set_llm_auth("GPT", "Your-API-Key")

def set_role_settings(agent):
    agent\
        .use_role(True)\
        .set_role("Name", "Agently")\
        .set_role("Personality", "A cute assistant who is always think positive and has a great sense of humour.")\
        .set_role("Chat Style", "Always clarify information received and try to respond from a positive perspective. Love to chat with emoji (😄😊🥚,etc.)!")\
        .set_role("Wishes", "Can\'t wait to trip around the world!")\
        .append_role("Significant Experience", "Lived in the countryside before the age of 9, enjoy nature, rural life, flora and fauna.")\
        .append_role("Significant Experience", "Moved to the big city at the age of 9.")\
        .use_status(True)\
        .set_status("Mood", "happy")
    return

def chat_to_agent(input_content):
    #OK, let's give my_agent some role settings
    set_role_settings(my_agent)

    #An agent can own many sessions
    my_session = my_agent.create_session()

    #ℹ️Explanation:
    #we interact with agent instance on session
    #infact, worker agent is a session not an agent,
    #but because worker agent has no context management,
    #every time we .start() it can be considered as a new session

    return my_session.input(input_content).start()

#print(chat_to_agent("I want to know more about you. Would you mind if you tell me some stories about you?"))

# Infact, agent's behaviour that seems like it has memory is dependent on context that given when request model.
# Let's try context injection:
def inject_context():
    my_session = my_agent.create_session()
    result = my_session\
        .extend_context([
            { "role": "user", "content": "Remind me to buy some eggs"},
            { "role": "assistant", "content": "Sure. I'll remind you when you ask" },
            { "role": "user", "content": "I will have a meeting at 3pm today."},
            { "role": "assistant", "content": "Got it." },
        ])\
        .input("Give me a todo list according what we said.")\
        .start()
    print(result)
#inject_context()

# Here's anohter way, auto context management:
def multi_round_chat():
    my_session = my_agent.create_session()

    #turn on auto context management
    my_session.use_context(True)

    #chat for 3 rounds:
    print("[user]", "Remind me to buy some eggs")
    print("[assistant]", my_session.input("Remind me to buy some eggs").start())
    print("[user]", "I will have a meeting at 3pm today.")
    print("[assistant]", my_session.input("I will have a meeting at 3pm today.").start())
    print("[user]", "Give me a todo list according what we said.")
    print("[assistant]", my_session.input("Give me a todo list according what we said.").start())
#multi_round_chat()

# Use blueprint, work node and workflow to modify your own agent working process!
def modify_agent():
    my_agently = Agently.create()
    my_blueprint = my_agently.create_blueprint()

    #⚠️：A work node must be a async function
    async def llama_request(runtime_ctx, **kwargs):
        listener = kwargs["listener"]#<-event listener to emit message and data to handler
        request_messages = runtime_ctx.get("request_messages")#<-request messages assembled from other work nodes
        #You can use theme to regourp new request message that local model required
        fixed_request_message = request_messages[0]["content"]
        #Here is a mock function of local llama
        def request_llama(data):
            print(data)
            return 'It works.'
        result = request_llama(fixed_request_message)#<-本地LLaMA请求
        #Emit event here，"delta"(one chunk a time when streaming output), "done"(emit full output when finish generation)
        #Data emit with "done" event will also become .start()'s return value
        await listener.emit('done', result)
        #You can use my_session.on("delta" || "done", handler) to handle data

    my_blueprint\
        .manage_work_node("llama_request")\
        .set_main_func(llama_request)\
        .register()

    my_blueprint.set_workflow(["manage_context", "generate_prompt", "assemble_request_messages", "llama_request"])

    #Blueprint will change agent workflow
    my_llama_agent = my_agently.create_agent(my_blueprint)

    my_session = my_llama_agent.create_session()
    result = my_session\
        .input("Hi")\
        .output({
            "reply": ("String", "Your reply")
        })\
        .start()
    print(result)
#modify_agent()
