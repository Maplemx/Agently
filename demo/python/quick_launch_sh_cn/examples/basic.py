import sys
import os
from dotenv import load_dotenv
import Agently
import blueprints

# 加载配置文件
load_dotenv('private_settings')

llm_name = os.getenv('llm_name')
group_id = os.getenv('group_id') 
api_key = os.getenv('api_key')
app_id = os.getenv('app_id')
api_secret = os.getenv('api_secret')
access_token = os.getenv('access_token')
wx_model_name = os.getenv('wx_model_name')
wx_model_type = os.getenv('wx_model_type')
llm_url = os.getenv('llm_url')
proxy = os.getenv('proxy')
blueprint_name = os.getenv('blueprint').replace('./examples/blueprints/','').replace('.py','')


print('已经加载: ', blueprint_name)

agently = Agently.create()
blueprint = blueprints.get_blueprint(blueprint_name)
agent = agently.create_agent(blueprint)
agent_name = agent.runtime_ctx.get("agent_name")
agent_name = agent_name if agent_name else "机器人"

#添加模型相关授权信息
agent.set_llm_name(llm_name)
if llm_name == "GPT":
    if not api_key:
        print("用户输入的 API-Key 为空，请提供有效的鉴权信息。")
        sys.exit(1)
    agent.set_llm_auth(llm_name, api_key)
    if llm_url:
        agent.set_llm_url(llm_name, llm_url)
    if proxy:
        agent.set_proxy(proxy)
elif llm_name == "MiniMax":
    if not group_id or not api_key:
        print("用户输入的 Group-id或API-Key 为空，请提供有效的鉴权信息。")
        sys.exit(1)
    agent.set_llm_auth(llm_name, { "group_id": group_id, "api_key": api_key })
    if llm_url:
        agent.set_llm_url(llm_name, llm_url)
elif llm_name == "Spark":
    if not app_id or not api_secret or not api_key:
        print("用户输入的 appid, API-Secret, API-Key 为空，请提供有效的鉴权信息。")
        sys.exit(1)
    agent.set_llm_auth(llm_name, { "app_id": app_id, "api_secret": api_secret, "api_key": api_key })
    if llm_url:
        agent.set_llm_url(llm_name, llm_url)
elif llm_name == "wenxin":
    if not access_token:
        print("用户输入的 access_token 为空，请提供有效的鉴权信息。")
        sys.exit(1)
    agent\
        .set_llm_auth(llm_name, access_token)\
        .set_wx_model_name(wx_model_name if wx_model_name != '' else 'qianfan_chinese_llama_2_7b')\
        .set_wx_model_type(wx_model_type if wx_model_type != '' else 'chat')
    if llm_url:
        agent.set_llm_url(llm_name, llm_url)

def generate_reply(user_input, session):
    reply = session\
        .input(user_input)\
        .start()
    return reply

def chatbot():
    session = agent.create_session()
    session.use_context(True)#<-开启一下agent的多轮会话自动记录
    print("欢迎使用多轮对话CLI界面！输入exit可以退出对话。")
    conversation = []
    while True:
        # 提示用户输入对话内容
        user_input = input("用户: ")
        
        # 将用户输入加入对话列表
        conversation.append(("用户", user_input))

        # 判断用户是否要结束对话
        if user_input.lower() == "exit":
            try:
                break
            except Exception as e:
                pass
        
        # 对用户输入进行处理并生成回复
        # 在这里替换成你的对话生成代码
        bot_reply = generate_reply(user_input, session)
        
        # 将机器人回复加入对话列表
        conversation.append((agent_name, bot_reply))
        
        # 输出机器人回复
        print(f"{ agent_name }: ", bot_reply)
    
    # 输出完整对话（暂时不需要）
    #print("对话记录：")
    #for role, content in conversation:
    #    print(role + ": " + content)

if __name__ == "__main__":
    chatbot()