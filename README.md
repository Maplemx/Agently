# Agently 3.0-Alpha版介绍手册

1.0及2.0版本说明手册可参见：[文档合集](https://github.com/Maplemx/Agently/tree/main/doc)

> 🥷 作者：Maplemx ｜ 📧 Email：maplemx@gmail.com | 💬 微信：moxinapp
>
> ⁉️ [如果您发现了BUG，或者有好的点子，请在这里提交](https://github.com/Maplemx/Agently/issues)
> 
>  ⭐️ 如果您觉得这个项目对您有帮助，请转发给您身边对大语言模型应用开发感兴趣的朋友，并给项目加星，感谢您的肯定和支持！
>
>  👾 Discord群组邀请链接：[https://discord.gg/j9CvXXJG](https://discord.gg/ufEk56Rk)
>
>  👥 微信讨论群：
> <img width="180" alt="image" src="https://github.com/Maplemx/Agently/assets/4413155/5fe467bb-e1c4-4550-9eaa-c59dc3221f58">
> 



3.0-Alpha版本安装方法：`pip install Agently==3.0.0a7`

> ⚠️3.0.0a6有一个小bug需要手动fix，[详情请参见](https://github.com/Maplemx/Agently/commit/45535d3d11b3502eedcd3aa5bae67f86dd1422a7)，将在下一个版本更新时修复

Github项目地址：[https://github.com/Maplemx/Agently](https://github.com/Maplemx/Agently)

<img width="1315" alt="image" src="https://github.com/Maplemx/Agently/assets/4413155/301729ea-8d26-4c40-9689-8e7c12a6ffbd">

## 让我们先来聊聊智能体（Agent）

随着以ChatGPT为代表的对话式语言模型交互界面的火爆出圈，越来越多的普通用户接触到了大型语言模型。对话式交互的简单易用，大型语言模型给出反馈时表现出的理解能力、表达能力、知识丰富程度甚至呈现出的一定的推理能力，都让用户惊叹不已。

这样聪明的表现，让人们对大型语言模型的期待也越来越高。

> “你能不能个性鲜明一点？”
> 
> “你能不能更了解这个世界在发生什么？”
> 
> “我希望你能更仔细地思考，而不是仓促回答”

这些都是我们听到的，真实用户在使用过ChatGPT或者类似的对话式大型语言模型应用之后发出的声音。

然而作为基于大型语言模型进行工程应用开发的开发者，我们知道，如果只是通过对大型语言模型简单地发起请求，用户的这些诉求是很难被满足的。因为大型语言模型本身并不能具备记忆、角色设定管理、主动感知这些能力，我们只能通过在每次请求中，向它提供充足的信息、给出更详细的指示来完成。

而如果我们要让用户依然能够用他们期待中的简单的交互方式去完成这些复杂的任务，就意味着我们需要在模型之上，构建出能够满足用户这种期待的工程结构体。而这个工程结构体就是我们所谓的智能体（Agent）

<img width="822" alt="image" src="https://github.com/Maplemx/Agently/assets/4413155/c2870366-575d-4fdb-a847-83feb1328d83">

如上图所示，智能体（Agent）基于大型语言模型提供的基础智力，通过不同的组件（Component）增强自身的能力，从而满足普通用户对大型语言模型的所有“幻觉”。

## 面向应用开发者：Agently提供方便快速生成能力强大的Agent实例的能力，让开发者可以便捷地将这些实例与自己的业务代码相结合

### 直观、清晰、结构化

如下面的代码示例所呈现的，Agently框架构建的Agent，能够为工程开发人员提供丰富的能力接口，用链式表达的方式，让工程开发人员条理清晰地表达自己的诉求，并获得结构化的数据返回结果。

整个过程直观易懂，Agent智能体以实例的形式存在，跟它的交互就像和一个实体对话一样简单。

```python
import Agently

# 创建一个Agent工厂实例
# 通过is_debug=True开启研发调试模式，获得更透明的过程信息
agent_factory = Agently.AgentFactory(is_debug=True)

# 设置工厂的配置项（这些配置项将被工厂生产的所有Agent继承）
agent_factory\
    .set_settings("model_settings.auth", { "api_key": GPT_API_KEY })\
    .set_settings("model_settings.url", GPT_BASE_URL)
    #.set_proxy("http://127.0.0.1:7890")

# 创建一个Agent实例
agent = agent_factory.create_agent()

# 利用agent实例提供的丰富能力接口进行诉求表达
# 链式表达的形式，让诉求表达结构清晰有条理
result = agent\
    .input("给我介绍一下北京周边的景点")\
    .output({
        "文化古迹": [({ "名称": ("String",), "介绍": ("String",) }, "具有历史特色的文化古迹景点")],
        "科技博览": [({ "名称": ("String",), "介绍": ("String",) }, "能够学习到博物、科技知识的景点")],
        "人文自然": [({ "名称": ("String",), "介绍": ("String",) }, "能够感受到人文自然之美的景点")],
    })\
    .start()
# 并在最终获得结构化的数据返回结果
print(result["人文自然"][0])
```
```ini
[输出结果]
{'名称': '颐和园', '介绍': '颐和园是中国古代皇家园林，位于北京西郊。它被誉为中国古典园林的瑰宝，是世界文化遗产。游览颐和园，可以欣赏到精美的建筑和优美的景观，感受到皇家园林的宁静和雅致。'}
```
### 通过组件获得能力增强

当然，Agently在应用开发层面的能力还不止这些。应用开发者们可以通过安装扩展组件的方式，获得进一步增强的能力。

例如：通过使用Role（角色管理）组件，获得动态管理角色设定、将角色设定持久化存储下来的能力。

```python
import Agently
# 使用框架提供的快速创建agent的方法创建一个agent实例
agent = Agently.create_agent()
# 通过agent实例上的角色设定方法，设定一个角色，并保存下来
agent\
    .set_role("You NEVER use any words EXCEPT EMOJI to response any question.")\
    .save_role("Emoji大玩家")
# 运行脚本让角色被持久化存储下来
```
```python
import Agently
# 在另一个脚本中创建一个新的agent实例
agent = Agently.create_agent()
# 给agent实例配置语言模型请求信息
agent\
    .set_settings("model_settings.auth", { "api_key": GPT_API_KEY })\
    .set_settings("model_settings.url", GPT_BASE_URL)
# 使用能力接口load_role加载之前设定好的角色
result = agent\
	.load_role("Emoji大玩家")\
	.input("给我讲一个中世纪骑士的故事")\
	.start()
print(result)
```
```ini
[输出结果]
🛡️🗡️🏰👑😇👼❤️🐴🗡️🏹💪🏻🐉🔥🏞️🛡️🗡️🏰💕👑🛡️🗡️🏰🔚
```
又例如：通过使用Segment（输出切块）组件，获得将一次请求分块处理的能力，在一次请求中，既获得流式输出的响应速度，又获得数据结构化输出的工程可用性。再结合ReplyReformer（输出结果重构）组件的能力，把最终的输出结果确定下来。

```python
# 准备一个用户标签存放的变量
user_tags = set([])

# 定义thinking阶段需要处理的任务
def handle_thinking(data):
    new_user_tags = set(data["user_tags"])
    user_tags.update(new_user_tags)

# 分成两段开始任务
# 第一段任务thinking在用户不可见的情况下完成问题类型的解析和用户标签的判断
# 第二段任务reply在用户可见的情况下进行流式输出，让用户快速看到答案
# 然后，通过reform_reply的能力接口，把result结果调整成reply部分的内容
result = agent\
    .input("能不能用一个程序员能听懂的表达方式，说明一下水蒸蛋的简易做法")\
    .segment(
        "thinking",
        {
            "question_type": (
                "专业技术问题 | 生活常识问题 | 闲聊 | 需要执行结果的任务 ",
                "{{input}}指向的问题类型"
            ),
            "user_tags": (
                "Array",
                "如果我要使用一些标签来描述用户的特征，例如职业、爱好、知识领域等，我应该怎么描述"
            ),
        },
        handle_thinking
    )\
    .segment(
        "reply",
        "对用户问题给出的直接回答",
        lambda data: print(data, end=""),
        is_streaming = True
    )\
    .reform_reply(
        lambda data: data['reply']['reply']
    )\
    .start()
# 最后我们把用户标签打印出来，看看用户不可见的后台操作是否顺利完成
print('[User Tags]', str(user_tags))
# 并把重新调整之后的result结果打印出来，看看是否符合我们的预期
print('[Result]', result)
```
```ini
[流式输出部分]
水蒸蛋的简易做法如下：
1. 准备材料：鸡蛋2个，清水适量，盐适量，葱花适量。
2. 打鸡蛋：将鸡蛋打入碗中，加入适量的盐，搅拌均匀。
3. 加水：在鸡蛋液中加入适量的清水，搅拌均匀。
4. 蒸煮：将葱花撒在蒸锅底部，将蛋液倒入蒸锅中，用中小火蒸煮约8-10分钟。
5. 完成：取出蒸好的水蒸蛋，撒上一些葱花作为装饰即可。可以口感更好的话，可以再加入一些调料，如酱油或番茄酱等。

希望这个简易做法对你有帮助，enjoy your meal！
[User Tags] {'程序员'}
[Result] 
水蒸蛋的简易做法如下：
1. 准备材料：鸡蛋2个，清水适量，盐适量，葱花适量。
2. 打鸡蛋：将鸡蛋打入碗中，加入适量的盐，搅拌均匀。
3. 加水：在鸡蛋液中加入适量的清水，搅拌均匀。
4. 蒸煮：将葱花撒在蒸锅底部，将蛋液倒入蒸锅中，用中小火蒸煮约8-10分钟。
5. 完成：取出蒸好的水蒸蛋，撒上一些葱花作为装饰即可。可以口感更好的话，可以再加入一些调料，如酱油或番茄酱等。

希望这个简易做法对你有帮助，enjoy your meal！
```
> ℹ️ Tips 1：更多模块能力可以查阅框架/plugins 文件夹的信息了解详情。
> 
> ℹ️ Tips 2：通过执行`agent.alias_manager.print_alias_info()`方法，可以查看当前的agent实例拥有的能力接口信息

### 和其他应用工程的结合

Agently提供的agent实例能够和其他应用工程库结合起来，应用到生产环境中。

在这里我们用Agently x tornado 为某个游戏场景搭建的websocket服务举例：

```python
import asyncio
import tornado.ioloop
import tornado.web
import tornado.websocket
import json
import Agently

agent_factory = Agently.AgentFactory(is_debug=True)
agent_factory\
    .set_settings("model_settings.auth", { "api_key": ENV.GPT_API_KEY })\
    .set_settings("model_settings.url", ENV.GPT_BASE_URL)

agent = agent_factory.create_agent()

# WebSocket 处理器
class WebSocketHandler(tornado.websocket.WebSocketHandler):
    async def on_message(self, message):
        try:
            data = json.loads(message)
            print("Data Received:", data)
            result = await agent\
                .set_role(data["role"])\
                .input({
                    "scene_desc": data["scene"],
                })\
                .segment(
                    "act",
                    "{{ROLE}}看到{{input.scene_desc}}描述的场景时的行动和话语",
                    lambda data: self.write_message(json.dumps({
                        "status": 200,
                        "data": { "event": "act", "delta": data },
                    })),
                    is_streaming=True
                )\
                .segment(
                    "action_options",
                    {
                        "action_options": [("String", "基于{{ROLE}}的设定和{{input.scene_desc}}的场景描述，生成不超过3个角色的后续行动选项描述，格式要求为'<行动名称>：<角色做出这个行动的心理活动和结果预期>'，例如'跳过深坑：看到这个深坑，我不确定自己是否真的能够跳过去，但是玛丽莲在对面等着我去救她，我必须努力一试，哪怕我可能摔个半死'")]
                    },
                    lambda data: self.write_message(json.dumps({
                        "status": 200,
                        "data": { "event": "action_options", "content": data }
                    })),
                    is_streaming=False
                )\
                .async_start()
            self.write_message(json.dumps({
                "status": 200,
                "data": { "event": "full_result", "content": result }
            }))
            self.close()
        except Exception as e:
            self.write_message(json.dumps({
                "status": 400,
                "msg": str(e),
            }))
            self.close()

# Web 应用
class Application(tornado.web.Application):
    def __init__(self):
        handlers = [("/game", WebSocketHandler)]
        super(Application, self).__init__(handlers)

if __name__ == "__main__":
    app = Application()
    app.listen(15365)
    print("WebSocket 服务已启动")
    tornado.ioloop.IOLoop.current().start()
```
```python
[Server端]
Data Received: {'role': '亚瑟，一个具有古典骑士精神的西部冒险者，热情、豪爽、不拘小节', 'scene': '森林的深处传来未知的响动，让人毛骨悚然。吉尔斯的话还回荡在耳边：“如果要追寻那未知的宝藏，胆小的人，还是尽快打道回府吧！”你回头看看伙伴，大家已经疲惫不堪，前进还是撤退？他们等待你的回答。'}
[Client端]
{'status': 200, 'data': {'event': 'act', 'delta': '\n'}}
{'status': 200, 'data': {'event': 'act', 'delta': '亚'}}
{'status': 200, 'data': {'event': 'act', 'delta': '瑟'}}
...
{'status': 200, 'data': {'event': 'act', 'delta': '是'}}
{'status': 200, 'data': {'event': 'act', 'delta': '什'}}
{'status': 200, 'data': {'event': 'act', 'delta': '么'}}
{'status': 200, 'data': {'event': 'act', 'delta': '！'}}
{'status': 200, 'data': {'event': 'act', 'delta': '”'}}
{'status': 200, 'data': {'event': 'act', 'delta': '\n'}}
{'status': 200, 'data': {'event': 'action_options', 'content': {'action_options': ['继续前进：亚瑟对伙伴们说道：“不管前方会有怎样的危险，我们都要勇往直前！只有这样，我们才能发现真正的宝藏之所在。”', '撤退回府：亚瑟考虑了一下伙伴们的疲惫，最终决定：“虽然内心渴望冒险，但现在的情况，我们还是先撤退回府，等大伙儿精神恢复再来探寻宝藏。”', '调查响动：亚瑟对伙伴们说道：“我们先调查一下那个未知的响动，看看是什么吓到了大家。也许这个线索能够帮助我们找到宝藏。”']}}}
{'status': 200, 'data': {'event': 'full_result', 'content': {'act': '\n亚瑟看到森林深处传来未知的响动，立刻展现出典型的冒险家精神，他毫不犹豫地迈向前方，眼中闪烁着探险的决心。他对吉尔斯说道：“胆小怕事的人只会错过这样的机遇！我们必须继续前进，看看那未知的宝藏究竟是什么！”\n', 'action_options': '\n{\n\t"action_options": \n\t[\n\t\t"继续前进：亚瑟对伙伴们说道：“不管前方会有怎样的危险，我们都要勇往直前！只有这样，我们才能发现真正的宝藏之所在。”",\n\t\t"撤退回府：亚瑟考虑了一下伙伴们的疲惫，最终决定：“虽然内心渴望冒险，但现在的情况，我们还是先撤退回府，等大伙儿精神恢复再来探寻宝藏。”",\n\t\t"调查响动：亚瑟对伙伴们说道：“我们先调查一下那个未知的响动，看看是什么吓到了大家。也许这个线索能够帮助我们找到宝藏。”"\n\t]\n}'}}}
```
从上面的例子可以看到，使用agent实例的async_start()方法，将agent的处理逻辑和Websocket的响应处理逻辑进行了结合。在游戏场景中，同时满足了快速向玩家进行场景表现输出，和为游戏系统生成后续行动选项的任务。

## 面向Agent开发者：用组件化的方式增量开发扩展Component，增强Agent的能力

（本部分内容仍在撰写中，感兴趣的朋友可以先查看[src/python/v3/plugins/agent_component](https://github.com/Maplemx/Agently/tree/main/src/python/v3/plugins/agent_component)的源代码了解设计思想）
