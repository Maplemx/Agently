# 为什么AI应用开发需要开发框架？

关于LangChain不好用的文章，隔一段时间就要来一次，核心论调往往是：
1. 抽象之上进行了抽象
2. 引入了太多新的概念而导致难以学习
3. ReAct Agent封装度过高，和实际场景不符
4. Custom Agent和Custom Chain太难用，不如手撸
5. AI应用无非就是模型调用+向量库检索而已

这里我无意针对这些论调直接讨论，也无意支持或反对LangChain的好与不好，而是想讨论“AI应用开发为什么需要开发框架”这个问题。

## AI应用隐藏了很多工程师需要学习的信息

直接调用大模型意味着有很多隐藏的认知和上下文信息需要工程师去进行前置学习和了解，例如：

- 模型连接调用：
    - 不同模型的连接配置（不仅仅输入参数格式管理，还要考虑输出格式）
    - 不同模型的提示词特性（因为Alignment不同，Prompt方式会存在差异）
    - 不同模型的流式输出适配
    - 不同模型的输出风格适配
- 模型控制理解：
    - Transformer的工作原理
    - In-Context Learning
    - 输出控制方法论
        - 结构化数据输出控制（如JSON）
        - 行为控制One Shot / Few Shots / CoT
        - 复杂任务控制方法：ReAct / 多轮请求链 / RAG
        - 特定场景控制方法：角色扮演类控制、文本分析类任务控制

## 虚假的业务场景：
- 我只需要模型调用+向量库就解决问题了（只能做做POC证明这件事能work）

## 真实的业务场景：
- 多步调用
- 复杂工作流编排
- 数据传输、数据共享、模型调用间通讯机制
- 经常性模型切换，同时要保持业务表达稳定性
- RAG≠读写向量库，写入前加工和读取后ReRank都需要根据业务场景定制
- 号池管理、多线程、并发、分布式
- 服务通讯
- 还得写得爽！脑子里不要乱轰轰的

## 好的框架应该：
- 封装隐藏底层复杂而又非业务的功能和逻辑
- 在业务表达上，用符合开发者直觉和习惯的方式，帮助开发者顺畅表达
- 对于高级开发者、定制需求，通过插件方式提供可插拔式更新方案
- 在开发过程中，提供足够的工具支持，帮助开发者理解代码运行状态
- 提供编码风格，帮助开发者群体形成开发范式和语言一致性，促进技术交流
- 提供最佳实践样例，帮助开发者提升代码规范度和可维护性
- 提供文档、教程、示例代码，帮助开发者快速解决问题
- （对于AI应用开发而言）提供业务开发者需要理解的基于模型能力的控制方法论，同时屏蔽业务开发者无需深度理解的各种底层知识

## Agently的目标是成为好的框架：
- 让开发者专注在业务开发上，单次请求由Agent对象代理，多轮请求编排由Workflow完成，都提供了简单顺畅的语法，业务开发的时候，思路极其顺滑
- 模型调用新增模型适配、Agent对象新增指令、存储方法新增数据存储类型，都通过插件完成
- 通过框架内部的架构设计，将模型适配、插件增强和业务表达三个层次完全解耦，任何一层的变动都不会严重冲击其他层，确保业务逻辑层表达的稳定性
- 文档丰富，社区热情，开发团队on call及时并乐于分享方法论
- 我们希望为AI应用开发者**降低开发门槛，提供高效、顺滑的开发体验**

## 举个直观的例子：
- 这是我们复现吴恩达博士Translation Agent项目的代码：

```python
import Agently

translation_workflow = Agently.Workflow()

@translation_workflow.chunk()
def user_input(inputs, storage):
  …
  return {
    "source_language": source_language,
    "target_language": target_language,
    "country": country,
    "source_text": source_text,
  }

@translation_workflow.chunk()
def initial_translation(inputs, storage):
  …
  return

@translation_workflow.chunk()
def reflect_on_translation(inputs, storage):
  # get data from storage
  source_language = storage.get("source_language")
  target_language = storage.get("target_language")
  country = storage.get("country")
  source_text = storage.get("source_text")
  initial_translation = storage.get("initial_translation")

  # create another agent because it has different role settings
  agent_factory = storage.get("agent_factory")
  reflect_on_translation_agent = agent_factory.create_agent()
  # set role (system-prompt-like)
  reflect_on_translation_agent.set_role(f"You are an expert linguist specializing in translation from {source_language} to {target_language}. You will be provided with a source text and its translation and your goal is to improve the translation.")
  # load commands from P-YAML to agent
  (
    reflect_on_translation_agent
      .load_yaml_prompt(
        path = "./prompt_yamls/reflect_on_translation.yaml",
        variables = {
          "source_language": source_language,
          "target_language": target_language,
          "source_text": source_text,
          "initial_translation": initial_translation
        }
      )
  )
  # append additional instruction when `country` is not empty
  if country and len(country) > 0:
    reflect_on_translation_agent.instruct([f"\nThe final style and tone of the translation should match the style of {target_language} colloquially spoken in {country}."])
  # give commands of current task and get reflection result
  print("\n[Reflection]:")
  reflection = (
    reflect_on_translation_agent
      # Streaming Output
      .on_delta(lambda data: print(data, end=""))
      .start()
  )
  # save reflection result to storage
  storage.set("reflection", reflection)
  return

@translation_workflow.chunk()
def improve_translation(inputs, storage):
  …
  return final_translation

(
  translation_workflow.chunks["start"]
    .connect_to(translation_workflow.chunks["user_input"])
    .connect_to(translation_workflow.chunks["initial_translation"])
    .connect_to(translation_workflow.chunks["reflect_on_translation"])
    .connect_to(translation_workflow.chunks["improve_translation"])
    .connect_to(translation_workflow.chunks["end"])
)
```
- 可以看到Agent代理的模型请求调用、代码分块、工作流连接关系管理，表达都非常清晰直观
- 完整代码可参考：https://github.com/Maplemx/translation-agent/tree/main/src/translation_agent_Agently
- 我们也有另一个可供参考的完整项目实践：
  - Agently-Daily-News-Collector（帮助你生成新闻日报的全自动工作流）：https://github.com/AgentEra/Agently-Daily-News-Collector

如果看到这里你对我们感兴趣，可以访问：http://Agently.cn 或是 https://github.com/Maplemx/Agently 进一步了解我们的项目。

下面是我们的项目地址二维码和讨论群入群二维码：

<img width="340" alt="image" src="https://github.com/Maplemx/Agently/assets/4413155/c030c16f-cd79-436e-90c0-3181bb636715">

<img width="540" alt="image" src="https://github.com/Maplemx/Agently/assets/4413155/4a6e1ea7-1602-407e-a5f6-b0b34ec6451f">

