import Agently
agent_factory = Agently.AgentFactory(is_debug = True)

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

agent\
    .input({
        "table_meta": meta_data["table_meta"],
        "question": "How can I check how many level 4 female customer have ordered in Jun. 2022 and how much money do they spend that month?"
    })\
    .instruct([
        "output SQL to query the database according meta data:{table_meta} that can anwser the question:{question}",
        "output language: Chinese",
    ])\
    .output({
        "thinkings": ("Array", "Your problem solving thinking step by step"),
        "SQL": ("String", "final SQL only"),
    })\
    .start()