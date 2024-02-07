import Agently
agent_factory = Agently.AgentFactory(is_debug=True)
agent_factory\
    .set_settings("current_model", "OpenAI")\
    .set_settings("model.OpenAI.auth", {"api_key": "Your-API-Key-API-KEY"})\
    .set_settings("model.OpenAI.url", "YOUR-BASE-URL-IF-NEEDED")

# 第 1 步，创建 Workflow 实例
workflow = Agently.Workflow()

# 第 2 步，实现 “判断用户意图是购物还是闲聊，路由到情感专家 or 销售导购” 的效果
#
#                                             --> 销   售
#     启动 --> 用户输入 --> 意图判断 --> 意图路由               --> 输出
#                                             --> 情感专家
#

# 2.1 创建 chunk 节点（chunk 的类型可以使用 workflow.executor.regist_executor 注册）

# 入口节点
start_chunk = workflow.schema.create_chunk(
    title = '一个例子',
    type = 'Start'
)

# 用户输入
def input_executor(inputs_pkg, store):
    user_input = input('有什么我能帮你的吗？')
    store.save('用户问题', user_input) # 暂存数据
    return user_input

wait_user_input_chunk = workflow.schema.create_chunk(
    title = '接收用户输入',
    executor = input_executor
)

# 意图判断节点
judge_agent = agent_factory.create_agent()
judge_chunk = workflow.schema.create_chunk(
    title='意图判断',
    executor=lambda inputs_pkg, store: judge_agent.input(inputs_pkg['用户问题']).set_role('导购').instruct('判断用户意图是“闲聊”还是“购物”').output({
        '用户意图': ('String', '\"闲聊\" 还是 \"购物\"')
    }).start(),
    handles = {
        "inputs": [{"handle": "用户问题"}],
        "outputs": [{"handle": "用户意图"}]
    }
)

# 销售
sales_agent = agent_factory.create_agent()
sales_agent_chunk = workflow.schema.create_chunk(
    title='销售',
    executor=lambda inputs_pkg, store: sales_agent.input(store.get('用户问题')).set_role('百货超市的销售').instruct('向用户推销产品，引导用户购买').output({
        '回复': ('String', '回答用户的问题')
    }).start(),
    handles = {
        "inputs": [{"handle": "用户问题"}],
        "outputs": [{"handle": "回复"}]
    }
)

# 情感专家
chat_agent = agent_factory.create_agent()
chat_agent_chunk = workflow.schema.create_chunk(
    title = '情感专家',
    executor=lambda inputs_pkg, store: chat_agent.input(store.get('用户问题')).set_role('情感专家').output({
        '回复': ('String', '回答用户的问题')
    }).start(),
    handles = {
        "inputs": [{"handle": "用户问题"}],
        "outputs": [{"handle": "回复"}]
    }
)

# 最终的输出打印
output_chunk = workflow.schema.create_chunk(
    executor=lambda inputs_pkg, store: print('[Result]', inputs_pkg)
)

# 3.2 按要求连接各个 chunk
start_chunk.connect_to(wait_user_input_chunk)  # 从起点出发，连接到 ”用户输入节点“

wait_user_input_chunk.connect_to(judge_chunk)  # 将 ”用户输入“ 的内容连接到 ”意图识别“

# 将 ”意图识别“ 的 "用户意图" 结果，连接到 ”判断路由“ 做判断
(
judge_chunk.handle('用户意图')
    .if_condition(lambda target: target == '购物').connect_to(sales_agent_chunk) # 如果是购物，则路由到 ”销售“
    .else_condition().connect_to(chat_agent_chunk) # 否则，路由到 ”情感专家“
)

sales_agent_chunk.connect_to(output_chunk)  # 最后将 ”销售“ 的回复返回
chat_agent_chunk.connect_to(output_chunk)  # 最后将 ”情感专家" 的回复返回

# 第 4 步，执行
workflow.startup()
