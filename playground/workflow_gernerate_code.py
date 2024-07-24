import Agently
import subprocess

"""
根据用户输入的要求生成代码，在本地通过subprocess调用python执行代码执行生成代码，如运行发生错误，反馈错误，用户补充信息和前一轮生成的代码给llm，重新生成代码。
"""
agent = (
    Agently.create_agent()
    .set_settings("current_model", "OpenAI") \
    .set_settings("model.OpenAI.auth", {"api_key": "填入你的api-key"}) \
    .set_settings("model.OpenAI.options", {"model": "gpt-4o-all"}) \
    )
workflow = Agently.Workflow()


@workflow.chunk()
def generate_code(inputs, storage):
    if storage.get("question") is not None:
        question = storage.get("question")
    else:
        question = input("[User]: ")
    storage.set("question", question)
    additional_context = storage.get("additional_context", "")

    history_code = storage.get("history_code", "")
    if history_code != "":
        history_code = history_code["code"]
    prompt = f"{question}\n此前代码:\n{history_code}\n{additional_context}"
    print(prompt)
    code = (
        agent
        .general("输出规定", "输出可以运行的python代码,不要包含任何解释说明，不要包含markdown语法")
        .info("python代码要求", "必须有print语句显示运行结果")
        .set_role("工作规则，"
                  "1：如果用户输入中包含第三方package，必须先搜索package的使用说明，使用正确的，未过时的函数名称和参数名称。"
                  "2：如果返回的additional_context中包含错误信息，根据错误信息，修改代码。")
        .input(prompt)
        .output({"code": ("str", "return python code")})
        .start()
    )
    storage.set("generated_code", code)
    storage.set("history_code", code)
    print("[Generated Code]:", code)
    return code


@workflow.chunk()
def execute_code(inputs, storage):
    code = storage.get("generated_code")["code"]
    print(type(code))
    print(code)
    try:
        result = subprocess.check_output(["python", "-c", code], stderr=subprocess.STDOUT, text=True, encoding='utf-8')
        print(result)
        storage.set("execution_result", result)
        return {"success": True}
    except subprocess.CalledProcessError as e:
        storage.set("execution_error", e.output)
        print("[Execution Error]:", e.output)
        return {"success": False}


@workflow.chunk()
def check_execution(inputs, storage):
    print("inputs:", inputs)
    if inputs["default"]["success"]:
        result = storage.get("execution_result")
        print("[Execution Result]:", result)
    else:
        error = storage.get("execution_error")
        print("[Execution Error]:", error)

    user_feedback = input("Is the program result correct? (Y/N): ")
    if user_feedback.upper() == "Y":
        return "success"
    else:
        if not inputs["default"]["success"]:
            storage.set("additional_context", storage.get("execution_error", "") + user_feedback.upper())
        else:
            storage.set("additional_context", user_feedback.upper())
        return "error"


@workflow.chunk()
def goodbye(inputs, storage):
    # 保存代码，把代码写入文件
    with open("generated_code.py", "w") as f:
        f.write(storage.get("generated_code")["code"])
    print("Bye~👋")
    return


workflow.connect_to("generate_code")
(
    workflow.chunks["generate_code"]
    .connect_to("execute_code")
)
workflow.chunks["execute_code"].connect_to("check_execution")

workflow.chunks["check_execution"].if_condition(lambda return_value, storage: return_value == "success").connect_to(
    "goodbye").connect_to("end").else_condition().connect_to("generate_code")

workflow.start()

# eg 读取本地图片file_path="face.png",使用红色方框标记所有人脸，并在图片左上角打印每个方框中心点的坐标[(x,y),(x,y)]
# User intervention 坐标点不要打印在方框的上方，而是用列表的方式打印在图片的左上角，方框的中心点用绿色标记出来。
