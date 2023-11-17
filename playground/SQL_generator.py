import Agently
agent_factory = Agently.AgentFactory(is_debug = False)

agent_factory\
    .set_settings("current_model", "OpenAI")\
    .set_settings("model.OpenAI.auth", { "api_key": "Your-API-Key-API-KEY" })\
    .set_settings("model.OpenAI.url", "YOUR-BASE-URL-IF-NEEDED")

agent = agent_factory.create_agent()

meta_data = {
    "table_meta" : [
        {
            "table_name": "user",
            "columns": [
                { "column_name": "user_id", "desc": "identity of user", "value type": "Number" },
                { "column_name": "gender", "desc": "gender of user", "value type": ["male", "female"] },
                { "column_name": "age", "desc": "age of user", "value type": "Number" },
                { "column_name": "customer_level", "desc": "level of customer account", "value type": [1,2,3,4,5] },
            ]
        },
        {
            "table_name": "order",
            "columns": [
                { "column_name": "order_id", "desc": "identity of order", "value type": "Number" },
                { "column_name": "customer_user_id", "desc": "identity of customer, same value as user_id", "value type": "Number" },
                { "column_name": "item_name", "desc": "item name of this order", "value type": "String" },
                { "column_name": "item_number", "desc": "how many items to buy in this order", "value type": "Number" },
                { "column_name": "price", "desc": "how much of each item", "value type": "Number" },
                { "column_name": "date", "desc": "what date did this order happend", "value type": "Date" },
            ]
        },
    ]
}

is_finish = False
while not is_finish:
    question = input("请输入您的问题: ")
    show_thinking = None
    while str(show_thinking).lower() not in ("y", "n"):
        show_thinking = input("本次输出是否展现思考过程？[Y/N]: ")
    show_thinking = False if show_thinking.lower == "n" else True
    print("[正在生成...]")
    result = agent\
        .input({
            "table_meta": meta_data["table_meta"],
            "question": question
        })\
        .instruct([
            "output SQL to query the database according meta data:{table_meta} that can anwser the question:{question}",
            "output language: Chinese",
        ])\
        .output({
            "thinkings": ["String", "Your problem solving thinking step by step"],
            "SQL": ("String", "final SQL only"),
        })\
        .start()
    if show_thinking:
        thinking_process = "\n".join(result["thinkings"])
        print("[思考过程]\n", thinking_process)
    print("[SQL]\n", result["SQL"])
    while str(is_finish).lower() not in ("y", "n"):
        is_finish = input("是否结束？[Y/N]: ")
    is_finish = False if is_finish.lower() == "n" else True