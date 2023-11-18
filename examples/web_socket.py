'''
Server End
'''
import Agently

agent_factory = Agently.AgentFactory()

agent_factory\
    .set_settings("model_settings.auth", { "api_key": "Your-API-Key" })\
    .set_settings("model_settings.url", "Your-Base-URL-if-needed")

agent = agent_factory.create_agent('agent_server')
agent\
    .start_websocket_server()

'''
Client End
'''
import asyncio
import Agently

client = Agently.WebSocketClient().create_keep_alive(path="test_agent")
result = client\
    .send("alias", { "name": "input", "params": "Give me 7 words" })\
    .send("alias", { "name": "output", "params": [ [("String",)] ] })\
    .send("start")\
    .on("delta", lambda data: print(data, end=""))

print(result)

# Yes, you can use the client request the agent server 
# almost like the way you use the agent instance interface locally