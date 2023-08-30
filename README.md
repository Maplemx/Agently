# Agently 2.0

Python版`v2.0.0`：[中文](https://github.com/Maplemx/Agently/blob/main/README.md)

NodeJS版`v1.1.3`：[English](https://github.com/Maplemx/Agently/blob/main/README_node_v1_EN.md) | [中文](https://github.com/Maplemx/Agently/blob/main/README_node_v1_CN.md)

> 🥷 作者：Maplemx ｜ 📧 Email：maplemx@gmail.com | 💬 微信：moxinapp
>
> ⁉️ [如果您发现了BUG，或者有好的点子，请在这里提交](https://github.com/Maplemx/Agently/issues)
> 
>  ⭐️ 如果您觉得这个项目对您有帮助，请给项目加星，感谢您的肯定和支持！
>
>  👥 微信讨论群二维码：
>
> <img src="https://github.com/Maplemx/Agently/assets/4413155/6a946ca5-e078-424a-80fc-93fa95e9f4de" width="128px" height="128px">
> 


## 通过Pip安装

`pip install Agently`

## 快速了解 Agently 2.0 可以做什么？

### ☄️ 用最快的速度开箱，在代码行中使用一个基础Agent的实例

```python
import Agently
worker = Agently.create_worker()
worker.set_llm_name("GPT").set_llm_auth("GPT", "Your-API-Key")
result = worker\
    .input("Give me 5 words and 1 sentence.")\
    .output({
        "words": ("Array",),
        "sentence": ("String",),
    })\
    .start()
print(result)
print(result["words"][2])
```

<details>
    <summary>运行结果</summary>

```
{'words': ['apple', 'banana', 'cat', 'dog', 'elephant'], 'sentence': 'I have a cat and a dog as pets.'}
cat
[Finished in 4.8s]
```

</details>

在上面的示例中，`worker`这个实例，就是一个基础Agent，它已经可以在代码中为我们工作，理解我们的输入要求（_input_），按照输出要求（_output_），生成对应结构的dict结果（_作为start()的运行结果，传递给result_）。而这一切，如果忽视为了链式表达的美观性而通过`\`进行的换行操作，其实都发生在一行代码里。

并且，你可能也注意到了，在Agently框架能力的支持下，面向Agent的请求表达，可以灵活使用各种代码数据结构（dict, list, tuple...）进行表达，并且可以期望获得符合这样数据结构的返回结果。

那么可能你会问，现在我的确在代码层面拥有了一个基础Agent，可是它又可以做什么呢？

下面是一些它可以做的事情的范例：

<details>
    <summary><span style = "font-size:115%; font-weight:bold">范例1：修复有格式错误的JSON字符串</span></summary>

示例代码：
    
```python
def fix_json(json_string, round_count = 0):
    round_count += 1
    try:
        json.loads(json_string)
        return json_string
    except json.JSONDecodeError as e:
        print("[Worker Agent Activated]: Round", round_count)
        print("Fix JSON Format Error:\n", e.msg)
        print("Origin String:\n", json_string, "\n")
        fixed_result = worker\
            .input({
                "origin JSON String": json_string,
                "error": e.msg,
                "position": e.pos,
            })\
            .output("Fixed JSON String only without explanation and decoration.")\
            .start()
        print("Fixed Content:\n", fixed_result, "\n")
        return fix_json(fixed_result)

result = fix_json("{'words': ['apple', 'banana', 'carrot', 'dog', 'elephant'], 'sentence': 'I have an apple, a banana, a carrot, a dog, and an elephant.'}")
print(result)
```

运行结果：

```
[Worker Agent Activated]: Round 1
Fix JSON Format Error:
 Expecting property name enclosed in double quotes
Origin String:
 {'words': ['apple', 'banana', 'carrot', 'dog', 'elephant'], 'sentence': 'I have an apple, a banana, a carrot, a dog, and an elephant.'} 

Fixed Content:
 {"words": ["apple", "banana", "carrot", "dog", "elephant"], "sentence": "I have an apple, a banana, a carrot, a dog, and an elephant."} 

{"words": ["apple", "banana", "carrot", "dog", "elephant"], "sentence": "I have an apple, a banana, a carrot, a dog, and an elephant."}
[Finished in 3.4s]
```

</details>

<details>
    <summary><span style = "font-size:115%; font-weight:bold">范例2：理解一句自然语言的输入，然后真实地调用某一个接口</span></summary>

```python
# 首先我们定义一下可用的工具
tools = {
    "weather_report": {
        "desc": "get weather report for the present time",
        "input_requirement": {
            "location": ("String", "your location")
        },
        "func": lambda **kwargs: print("The weather is sunny right now.\n", kwargs)
    },
    "weather_forecast": {
        "desc": "get weather forecast for the next 2-24 hours.",
        "input_requirement": {
            "location": ("String", "your location"),
        },
        "func": lambda **kwargs: print("There'll be raining 3 hours later.\n", kwargs)
    },
    "file_browser": {
        "desc": "Browse files that are given to.",
        "input_requirement": {
            "file_path": ("String", "File path that to be browsed."),
            "chunk_num": ("Number", "How many chunks to be output?"),
            "need_summarize": ("Boolean", "Do user need a summarize about the file?")
        },
        "func": lambda **kwargs: print("File browse work done.\n", kwargs)
    },
}

# 让Worker Agent自己决定是不是应该调用，以及应该如何调用对应的工具
def call_tools(natural_language_input):
    #step 1. 确定应该使用哪个工具
    tools_desc = []
    for tool_name, tool_info in tools.items():
        tools_desc.append({ "name": tool_name, "desc": tool_info["desc"] })
    tools_to_be_used = worker\
        .input({
            "input": natural_language_input,
            "tools": str(tools_desc)
        })\
        .output([("String", "Tool name in {{input.tools}} to response {{input}}'s requirement.")])\
        .start()
    #step 2. 生成调用工具所需要的参数，并真实地进行调用
    for tool_name in tools_to_be_used:
        call_parameters = worker\
            .input({
                "input": natural_language_input,
            })\
            .output(tools[tool_name]["input_requirement"])\
            .start()
        tools[tool_name]["func"](**call_parameters)
call_tools("Browse ./readme.pdf for me and chunk to 3 pieces without summarize and check Beijing's next 24 hours weather for me.")
```

运行结果：

```
File browse work done.
 {'file_path': './readme.pdf', 'chunk_num': 3, 'need_summarize': False}
There'll be raining 3 hours later.
 {'location': 'Beijing'}
[Finished in 8.1s]
```

</details>

### 👨‍👩‍👧‍👦 支持使用多种模型生成不同的Agent

或许你会需要在不同的场景下，让Agent切换使用不同的模型；或是想让基于不同模型（从而获得不同能力）的Agent之间相互协作。

使用Agently，你可以简单地用`.set_llm_name("<模型名称>")`设置你想要使用的模型名称，并使用`.set_llm_auth("<鉴权信息>")`提交对应的鉴权信息，就可以在官方支持的模型间进行切换，并且无需关心不同模型间的请求方式差异。

目前官方支持的模型名单：

- `GPT`：OpenAI GPT全系列
- `MiniMax`：MiniMax abab 5/abab 5.5
- `讯飞星火大模型`：（即将支持）
- `百度文心一言`：（即将支持）
- _更多可支持模型持续更新中，欢迎[到issues里许愿](https://github.com/Maplemx/Agently/issues)..._

目前还没有支持到你想要的模型，或者你想使用本地部署的模型，怎么办？

当然可以，继续往下看，在工作节点和工作流介绍里，Agently也给出了自己定制模型调用方法的解决方案。

### 🎭 你也可以管理Agent实例的人设、属性和记忆，将它打造成你想要的样子

基于Agently将所有的Agent都在代码层面对象化的设计思想，你可以方便地管理你的Agent实例的各种设定，比如人物基础设定、背景故事、行为特征、属性参数等，也可以通过context管理的方式，影响你的Agent的上下文记忆。

当然，你也可以用上下文记忆注入的方式，让你的Agent掌握更多的知识，或是学会某些外部接口的调用规则。

```python
import Agently
#首先，让我们创建一个新的Agent实例
my_agently = Agently()
my_agent = my_agently.create_agent()

#通过.set_role()/.append_role()
#和.set_status()/.append_status()的方法
#调整Agent的角色设定
my_agent\
    .set_role("姓名", "Agently小助手")\
    .set_role("性格", "一个可爱的小助手，非常乐观积极，总是会从好的一面想问题，并具有很强的幽默感。")\
    .set_role("对话风格", "总是会澄清确认自己所收到的信息，然后从积极的方面给出自己的回复，在对话的时候特别喜爱使用emoji，比如😄😊🥚等等!")\
    .set_role("特别心愿", "特别想要环游世界！想要去户外旅行和冒险！")\
    .append_role("背景故事", "9岁之前一直住在乡下老家，喜欢农家生活，喜欢大自然，喜欢在森林里奔跑，听鸟叫，和小动物玩耍")
    .append_role("背景故事", "9岁之后搬到了大城市里，开始了按部就班的生活，从学校到工作，一切充满了规律")
    .set_status("心情", "开心")

#通过.create_session()开启一次会话，并询问Agent她的故事
my_session = my_agent.create_session()
result = my_session.input("我想了解一下你，能给我讲讲你的故事吗？").start()
print(result)
```

<details>
    <summary>运行结果</summary>

```
当然可以！我很喜欢和你分享我的故事呢！我小时候，我住在一个美丽的乡下小镇上，那里有绿油油的田野，清澈透明的溪流，还有茂密的森林。我特别喜欢农家的生活，每天都可以在大自然中奔跑，聆听着鸟儿的歌唱，和小动物们玩耍。那种感觉真的很让人快乐呢！🌳🐦🌞

可是，当我9岁的时候，我和家人搬到了大城市。从此以后，我的生活变得按部就班，跟着学校和工作的规律。虽然城市生活有很多有趣的事情，但是我还是特别怀念乡下的自由和大自然的美好。所以，现在我希望有机会能环游世界，去户外旅行和冒险，重新感受大自然的魅力！😄🌍

希望我分享的故事能够让你对我有更多的了解！如果还有其他问题，我随时都可以回答哦！😊✨
[Finished in 20.5s]
```

</details>

### 🧩 使用工作节点（work node）和工作流（workflow），你甚至可以编排Agent的工作方法

在Agently 2.0里，可自定义Agent的工作节点（work node），并自定义Agent的整体工作流（workflow）是非常重要的架构设计更新。通过这样的编排能力，你可以构建出复杂的行为链条，甚至可以在Agent实例内实现ToT（思维树）、SoT（思维骨架）这样的复杂思考方式。

下面用一个简单的例子演示Agently如何通过修改`request`工作节点来适配本地部署的模型（模型实际调用方法不在本例的范围内）

```python
import Agently
my_agently = Agently.create()

'''
通过蓝图调整工作节点和工作流
'''

#首先创建一个蓝图实例
my_blueprint = my_agently.create_blueprint()

#定义新的模型请求节点的主要处理函数
async def llama_request(runtime_ctx, **kwargs):#<-⚠️：这里必须是异步
    listener = kwargs["listener"]#<-这是消息监听器，通过它来向外传递消息
    #runtime_ctx是节点间用于共享信息的工具
    #你可以使用它的.set()和.get()方法在不同的工作节点间进行消息互传
    request_messages = runtime_ctx.get("request_messages")#<-这是收集到的请求消息信息
    #可以改造请求消息信息，来适配其他模型的需要
    fixed_request_message = request_messages[0]["content"]
    #模拟一个本地请求
    def request_llama(data):
        print(data)
        return 'It works.'
    result = request_llama(fixed_request_message)#<-本地LLaMA请求
    #在这里分发结果消息，通常有"delta"（流式请求中的一个chunk），和"done"两种，"done"方法发送的数据会自动成为请求的结果
    await listener.emit('done', result)
    #发出的消息可以在my_session.on("done", handler)里截获并被handler处理

#将主要处理函数注册到蓝图的节点中
my_blueprint\
    .manage_work_node("llama_request")\
    .set_main_func(llama_request)\
    .register()

#重新编排蓝图的工作流（节点将顺次执行）
my_blueprint.set_workflow(["manage_context", "generate_prompt", "assemble_request_messages", "llama_request"])

#装载蓝图，改变agent的工作逻辑
my_llama_agent = my_agently.create_agent(my_blueprint)

my_session = my_llama_agent.create_session()
result = my_session\
    .input("你好")\
    .output({
        "reply": ("String", "你的回复")
    })\
    .start()
print(result)
```
<details>
    <summary>运行结果</summary>

```
# INPUT:
你好

# OUTPUT REQUIREMENT:
## TYPE:
JSON String can be parsed in Python
## FORMAT:
{
    "reply": <String>,//你的回复
}


# OUTPUT:

It works.
[Finished in 207ms]
```

</details>

可以看到，在上面的例子中，Agent的工作流程已经正确地被修改为自定义的方案，在模拟本地请求的函数里输出了获取到的请求信息，并在session请求的最终输出里，正确输出了模拟本地请求的函数返回的"It works."信息。

###  👥 通过蓝图发布你定制的独特Agent给更多人使用

细心的小伙伴可能已经注意到，在上一段案例中，我们使用了蓝图（blueprint）这个实例进行工作流编排，然后在真正的Agent实例创建时，通过蓝图把能力装载到了Agent身上。

其实，蓝图除了工作流编排外，也可以像Agent一样，进行人设和状态管理，然后通过装载的方式，把这些设定都复制到新创建的Agent实例上。

那么，通过分享蓝图代码，就可以方便地让其他小伙伴使用蓝图，根据你做好的Agent方案创建Agent实例啦！

这也是Agently 2.0在架构升级时，从支持社群贡献的角度做出的重要设计。

---

以上就是对Agently 2.0 Python版的快速介绍，如果你喜欢这个项目，请去[github.com/Maplemx/Agently](https://github.com/Maplemx/Agently)给我加个⭐️吧！