import sys
import os
from dotenv import load_dotenv
import Agently

# 加载配置文件
load_dotenv('private_settings')

llm_name = os.getenv('llm_name')
group_id = os.getenv('group_id') 
api_key = os.getenv('api_key')
llm_url = os.getenv('llm_url')
proxy = os.getenv('proxy')

if not api_key:
    print("用户输入的 KEY 为空，请提供有效的 KEY。")
    sys.exit(1)

agently = Agently.create()
agent = agently.create_agent()#<-把它替换成你们自己做的agent实例

#添加模型相关授权信息
agent.set_llm_name(llm_name)
if llm_name == "GPT":
    agent.set_llm_auth(llm_name, api_key)
    if llm_url:
        agent.set_llm_url(llm_url)
    if proxy:
        agent.set_proxy(proxy)
elif llm_name == "MiniMax":
    agent.set_llm_auth(llm_name, { "group_id": group_id, "api_key": api_key })
    if llm_url:
        agent.set_llm_url(llm_url)

def generate_reply(user_input, session):
    reply = session\
        .input(user_input)\
        .start()
    return reply

def chatbot():
    session = agent.create_session()
    session.use_context(True)#<-开启一下agent的多轮会话自动记录
    print("欢迎使用多轮对话CLI界面！")
    conversation = []
    while True:
        # 提示用户输入对话内容
        user_input = input("用户：")
        
        # 将用户输入加入对话列表
        conversation.append(("USER", user_input))
        
        # 对用户输入进行处理并生成回复
        # 在这里替换成你的对话生成代码
        bot_reply = generate_reply(user_input, session)
        
        # 将机器人回复加入对话列表
        conversation.append(("BOT", bot_reply))
        
        # 输出机器人回复
        print("机器人：", bot_reply)
        
        # 判断用户是否要结束对话
        if user_input.lower() == "结束对话":
            break
    
    # 输出完整对话
    print("对话记录：")
    for role, content in conversation:
        print(role + ": " + content)

if __name__ == "__main__":
    chatbot()