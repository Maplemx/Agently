import asyncio
import v2 as Agently

agently = Agently.create()
agently.set("is_debug", False)

agent = agently.create_agent()
agent\
    .set_llm_auth("GPT", "Your-API-Key")\
    .set_request_options("GPT", { "model": "gpt-4" })\
#    .set_proxy("http://127.0.0.1:7890")

product_designer = agently.create_agent()

product_designer\
    .set("llm_auth",{ "GPT": "Your-API-Key" })\
    .use_role(True)\
    .set_role("Role Desc", "You ara a professor of product design, to analyze target requirement and state parts that to be build in application.")

python_coder = agently.create_agent()

python_coder\
    .set("llm_auth",{ "GPT": "Your-API-Key" })\
    .use_role(True)\
    .set_role("Role Desc", "You ara a professor of python coding that only output code without explanation.")

code_advisor = agently.create_agent()

code_advisor\
    .set("llm_auth",{ "GPT": "Your-API-Key" })\
    .use_role(True)\
    .set_role("Role Desc", "You ara a professor of all kind of program coding, you can anwser all questions about coding.")

code_content = ''

def save_code(addition_code):
    code_content += addition_code + '\n'

env_box = agently.create_env_box()

result = env_box\
    .set_target("用python开发一个可以运行的贪食蛇小游戏")\
    .set_options("show_process", True)\
    .set_overwatcher(agent)\
    .register_agent(
        "code_advisor",
        "agent who you can turn to ask knowledge about coding.",
        code_advisor,
    )\
    .register_agent(
        "python_coder",
        "agent who can generate python code that can run",
        python_coder,
    )\
    .register_agent(
        "product_designer",
        "agent who can design product functions and output product document",
        product_designer,
    )\
    .register_func(
        "save_code",
        "func to save your generated code",
        {
            "addition_code": ("String",),
        },
        save_code
    )\
    .start()

print('Final Result\n', result)
print('Code\n', code_content)
