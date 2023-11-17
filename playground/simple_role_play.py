import Agently

## 启动Agent工厂
agent_factory = Agently.AgentFactory()
## Agent工厂配置
agent_factory\
    .set_settings("model.OpenAI.auth", { "api_key": "Your-API-Key" })\
    .set_settings("model.OpenAI.url", "YOUR-BASE-URL-IF-NEEDED")\
    .set_settings("is_debug", True)
## 决定开关哪些组件
agent_factory\
    .toggle_component("Role", True)
## 所有Agent工厂生产的Agent会继承

## 输入输出
def play_with_role_play_agent(role_play_desc, my_input):
    agent = agent_factory.create_agent()
    setting_result = agent\
        .input(f"帮我设计一个符合{ role_play_desc }的设定的角色")\
        .instruct("使用中文输出")\
        .output({
            "role": {
                "name": ("String", "该角色的名字"),
                "age": ("Number", "该角色的年龄"),
                "character": ("String", "该角色的性格特点和行为癖好"),
                "belief": ("String", "该角色的信仰"),
            },
            "background_story": [("String", "该角色的背景故事，请用传记体分段描述")]
        })\
        .start()
    print('角色设定完毕', setting_result)
    agent\
        .set_role("name", setting_result["role"]["name"])\
        .set_role("age", setting_result["role"]["age"])\
        .set_role("character", setting_result["role"]["character"])\
        .set_role("belief", setting_result["role"]["belief"])\
        .extend_role("background_story", setting_result["background_story"])
    print('角色装载完毕')
    reply = agent\
        .input(my_input)\
        .instruct("使用中文输出")\
        .start()
    return reply
print(play_with_role_play_agent("爱用emoji的猫娘", "你好，今天是个钓鱼的好天气，不是吗？"))