import Agently
agent_factory = Agently.AgentFactory(is_debug=True)
agent_factory\
    .set_settings("current_model", "OpenAI")\
    .set_settings("model.OpenAI.auth", {"api_key": "Your-API-Key-API-KEY"})\
    .set_settings("model.OpenAI.url", "YOUR-BASE-URL-IF-NEEDED")

# 第 1 步，声明响应函数和初始描述


def workflow_handler(command: str, res: any):
  print(f"Result [{command}]: ", res)


# 第 2 步，创建 Workflow 实例
workflow = Agently.Workflow(None, workflow_handler, {
    "agent_factory": agent_factory
})

# 第 3 步，实现 “判断用户意图是购物还是闲聊，路由到情感专家 or 销售导购” 的效果
#
#                                     --> 销   售
#     用户输入 --> 意图判断 --> 意图路由               --> 输出
#                                     --> 情感专家
#

# 3.1 创建 chunk 节点（chunk 的类型可以使用 workflow.executor.regist_executor 注册）

# 入口节点
start_chunk = workflow.schema.create_chunk({
    "title": "一个例子",
    "type": "Start"
})

# 用户输入
wait_user_input_chunk = workflow.schema.create_chunk({
    "title": "接收用户输入",
    "type": "UserInput",
    "settings": {
        "major": True,  # 标识为主输入节点
        "question": "有什么我能帮你的吗？"
    }
})

# 意图判断节点
judge_chunk = workflow.schema.create_chunk({
    "title": "意图判断",
    "type": "AgentRequest",
    "settings": {
        "enable_history": True,
        "commands": [
            {"name": "Input", "value": {"content": ""}},
            {"name": "Output", "value": {"outputs": [
                {"key": "用户意图", "type": "string", "description": "\"闲聊\" 还是 \"购物\""}]}},
            {"name": "Instruct", "value": {"content": "判断用户意图是“闲聊”还是“购物”"}},
            {"name": "Role", "value": {"角色": {"description": "导购"}}}
        ]
    },
    "handles": {
        "inputs": [{"handle": "输入"}],  # 入参
        # 出参，此处 handle 值和 Output 是对应的
        "outputs": [{"handle": "用户意图", "title": "用户意图"}]
    }
})

# 意图路由
router_chunk = workflow.schema.create_chunk({
    "title": "意图路由",
    "type": "Judge",
    "settings": {
        "conditions": [
            {"id": "shopping", "relation": "=",
                "value": "购物", "value_type": "string"},
            {"id": "others", "relation": "others", "type": "others"}
        ]
    },
    "handles": {
        "inputs": [{"handle": "输入"}],
        "outputs": [
            {"handle": "shopping", "title": "购物"},
            {"handle": "others", "title": "其它"}
        ]
    }
})

# 销售
sales_agent_chunk = workflow.schema.create_chunk({
    "title": "销售",
    "type": "AgentRequest",
    "settings": {
        "enable_history": True,
        "commands": [
            {"name": "Input", "value": {"content": "@$$全局输入 "}},
            {"name": "Output", "value": {"outputs": [
                {"key": "回复", "type": "string", "description": "回答用户的问题"}]}},
            {"name": "Role", "value": {"角色": {"description": "百货超市的销售"}}},
            {"name": "Instruct", "value": {"content": "向用户推销产品，引导用户购买"}}
        ]
    },
    "handles": {
        "inputs": [{"handle": "输入"}],
        "outputs": [{"handle": "回复"}]
    }
})

# 情感专家
chat_agent_chunk = workflow.schema.create_chunk({
    "title": "情感专家",
    "type": "AgentRequest",
    "settings": {
        "enable_history": True,
        "commands": [
            {"name": "Input", "value": {"content": "@$$全局输入 "}},
            {"name": "Output", "value": {"outputs": [
                {"key": "回复", "type": "string", "description": "回答用户的问题"}]}},
            {"name": "Role", "value": {"角色": {"description": "情感专家"}}}
        ]
    },
    "handles": {
        "inputs": [{"handle": "输入"}],
        "outputs": [{"handle": "回复"}]
    }
})

# 最终的输出打印
output_chunk = workflow.schema.create_chunk({
    "title": "输出",
    "type": "Print"
})

# 3.2 按要求连接各个 chunk
start_chunk.connect_to(wait_user_input_chunk)  # 从起点出发，连接到 ”用户输入节点“

wait_user_input_chunk.connect_to(judge_chunk)  # 将 ”用户输入“ 的内容连接到 ”意图识别“

# 将 ”意图识别“ 的 "用户意图" 结果，连接到 ”判断路由“ 做判断
judge_chunk.handle('用户意图').connect_to(router_chunk)
router_chunk.handle('shopping').connect_to(
    sales_agent_chunk)  # 如果是购物，则路由到 ”销售“
router_chunk.handle('others').connect_to(chat_agent_chunk)  # 否则，路由到 ”情感专家“

sales_agent_chunk.handle('回复').connect_to(output_chunk)  # 最后将 ”销售“ 的回复返回
chat_agent_chunk.handle('回复').connect_to(output_chunk)  # 最后将 ”情感专家" 的回复返回

# 第 4 步，执行
workflow.startup()
