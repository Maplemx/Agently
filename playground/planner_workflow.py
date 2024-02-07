import Agently
agent_factory = Agently.AgentFactory(is_debug=True)
agent_factory\
    .set_settings("current_model", "OpenAI")\
    .set_settings("model.OpenAI.auth", {"api_key": "Your-API-Key-API-KEY"})\
    .set_settings("model.OpenAI.url", "YOUR-BASE-URL-IF-NEEDED")

# 第 1 步，创建 Workflow 实例
workflow = Agently.Workflow(settings = {
    "max_execution_limit": 20
})

# 第 3 步，流程编排
#
#     启动 --> 生成策划问题，判断信息完整度 -- [完整] --> 活动策划 --> 输出
#                ↑                  |
#            提问并收集信息 _[不完整]__|
#                                     

# 3.1 创建 chunk 节点（chunk 的类型可以使用 workflow.executor.regist_executor 注册）
# 入口节点
start_chunk = workflow.schema.create_chunk(
    title = "活动方案策划",
    type = "Start"
)

"""生成策划问题，判断信息完整度"""
question_design_agent = agent_factory.create_agent()
questions_design_chunk = workflow.schema.create_chunk(
    title = "策划问题生成及判断节点",
    executor=lambda inputs_pkg, store: (
        question_design_agent
            .input('\n'.join(store.get('已收集的信息', [])))
            .set_role('活动策划师')
            .instruct('根据用户问题及已收集的信息，判断要策划一个活动，是否还需要额外信息，如果需要则给出收集活动信息的提问')
            .output({'提问清单': [('String', '待收集信息的提问问题清单(一次不多于3个)')], '收集完成': ('Boolean', '判断信息是否已收集完成')})
            .start()
    ),
    handles={
        "inputs": [{"handle": "输入"}],
        "outputs": [{"handle": "提问清单"}, {"handle": "收集完成"}]
    }
)

"""收集用户问题"""
collect_user_info_chunk = workflow.schema.create_chunk(
    title="提问并收集信息",
    executor=lambda inputs_pkg, store: store.save(
      '已收集的信息',
      store.get('已收集的信息', []) +
        [f'{question or "Please input:"}: {input(question or "Please input:")}' for question in inputs_pkg['问题清单']]
    ),
    handles={
        "inputs": [{"handle": "问题清单"}, {"handle": "启动"}],
        "outputs": [{"handle": "用户回答"}]
    }
)

"""活动策划"""
planner_agent = agent_factory.create_agent()
planner_chunk = workflow.schema.create_chunk(
    title='活动策划',
    executor=lambda inputs_pkg, store: (
        planner_agent
            .input('\n'.join(store.get('已收集的信息', [])))
            .set_role('活动策划师')
            .instruct('根据给到的信息，策划一个完整的活动方案')
            .output({'策划方案': ('String', '策划方案')})
            .start()
    ),
    handles={
        "inputs": [{"handle": "输入"}],
        "outputs": [{"handle": "策划方案"}]
    }
)

"""最终的输出打印"""
output_chunk = workflow.schema.create_chunk(
  title='输出',
  executor = lambda inputs_pkg, store: print('Result: ', inputs_pkg)
)

# 3.2 按要求连接各个 chunk
start_chunk.connect_to(questions_design_chunk)  # 从起点出发，连接到 ”策划问题生成节点“

# 将 ”策划问题生成节点“ 的提问清单结果连接到 ”提问并收集信息节点“
questions_design_chunk.handle('提问清单').connect_to(
    collect_user_info_chunk.handle('问题清单'))

def judge_finished(is_finished):
  print('judge finished', is_finished)
  return is_finished == True
# 如果信息已完整，则连接到 ”活动策划节点“ 开始策划，否则，找用户提问，直到信息收集完整
(
questions_design_chunk.handle('收集完成')
    .if_condition(judge_finished)
        .connect_to(planner_chunk)
    .else_condition()
        .connect_to(collect_user_info_chunk.handle('启动'))
)

# 用户回答完本轮问题后，将用户的回答信息交给 "策划问题生成节点" ，继续判断信息是否完整
collect_user_info_chunk.connect_to(questions_design_chunk)

# 最后将 ”活动策划" 结果返回
planner_chunk.connect_to(output_chunk)

# 第 4 步，执行
workflow.startup()