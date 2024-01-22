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

# 第 3 步，流程编排
#
#     启动 --> 生成策划问题，判断信息完整度 -- [完整] --> 活动策划 --> 输出
#                ↑                  |
#            提问并收集信息 _[不完整]__|
#                                     
#

# 3.1 创建 chunk 节点（chunk 的类型可以使用 workflow.executor.regist_executor 注册）
# 入口节点
start_chunk = workflow.schema.create_chunk({
    "title": "活动方案策划",
    "type": "Start"
})

# 生成策划问题，判断信息完整度
questions_design_chunk = workflow.schema.create_chunk({
    "title": "策划问题生成及判断节点",
    "type": "AgentRequest",
    "settings": {
        "enable_history": True,
        "commands": [
            {"name": "Input", "value": {"content": "@$$全局输入 "}},
            {"name": "Output", "value": {"outputs": [
                {"key": "提问清单", "type": "list",
                 "description": "待收集信息的提问问题清单(一次不多于3个)"},
                {"key": "收集完成", "type": "boolean", "description": "判断信息是否已收集完成"}
            ]}},
            {"name": "Role", "value": {"角色": {"description": "活动策划师"}}},
            {"name": "Instruct", "value": {
                "content": "根据用户问题及已收集的信息，判断要策划一个活动，是否还需要额外信息，如果需要则给出收集活动信息的提问"}}
        ],
    },
    "handles": {
        "inputs": [{"handle": "输入"}],
        "outputs": [{"handle": "提问清单"}, {"handle": "收集完成"}]
    }
})

# 判断信息是否完整
judge_router_chunk = workflow.schema.create_chunk({
    "title": "信息完整度判断节点",
    "type": "Judge",
    "settings": {
        "conditions": [
            {"id": "finished", "relation": "=",
             "value": "True", "value_type": "boolean"},
            {"id": "others", "relation": "others", "type": "others"}
        ]
    },
    "handles": {
        "inputs": [{"handle": "输入"}],
        "outputs": [
            {"handle": "finished", "title": "已完成"},
            {"handle": "others", "title": "未完成"}
        ]
    }
})

collect_user_info_chunk = workflow.schema.create_chunk({
    "title": "提问并收集信息",
    "type": "UserInput",
    "settings": {
        "major": True,  # 标识为主输入节点
    },
    "handles": {
        "inputs": [{"handle": "input", "title": "问题清单"}, {"handle": "start", "title": "启动"}],
        "outputs": [{"handle": "信息"}]
    }
})

# 活动策划
planner_chunk = workflow.schema.create_chunk({
    "title": "活动策划",
    "type": "AgentRequest",
    "settings": {
        "enable_history": True,
        "commands": [
            {"name": "Input", "value": {"content": "@$$全局输入 "}},
            {"name": "Output", "value": {"outputs": [
                {"key": "策划方案", "type": "string", "description": "策划方案"}]}},
            {"name": "Instruct", "value": {"content": "根据给到的信息，策划一个完整的活动方案"}},
            {"name": "Role", "value": {"角色": {"description": "活动策划师"}}}
        ],
    },
    "handles": {
        "inputs": [{"handle": "输入"}],
        "outputs": [{"handle": "策划方案"}]
    }
})

# 最终的输出打印
output_chunk = workflow.schema.create_chunk({
    "title": "输出",
    "type": "Print"
})

# 3.2 按要求连接各个 chunk
start_chunk.connect_to(questions_design_chunk)  # 从起点出发，连接到 ”策划问题生成节点“

questions_design_chunk.handle('提问清单').connect_to(
    collect_user_info_chunk.handle('input'))  # 将 ”策划问题生成节点“ 的提问清单结果连接到 ”提问并收集信息节点“
questions_design_chunk.handle('收集完成').connect_to(
    judge_router_chunk)  # '是否完成' 连接到 ”信息完整度判断节点“

judge_router_chunk.handle('finished').connect_to(
    planner_chunk)  # 如果信息已完整，则连接到 ”活动策划节点“ 开始策划
judge_router_chunk.handle('others').connect_to(
    collect_user_info_chunk.handle('start'))  # 否则，找用户提问
# 用户回答完本轮问题后，跳转到 "策划问题生成节点" 继续生成新问题
collect_user_info_chunk.connect_to(questions_design_chunk)

planner_chunk.connect_to(output_chunk)  # 最后将 ”活动策划" 结果返回

# 第 4 步，执行
workflow.startup()
