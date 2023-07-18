//如何使用？
// 第一步：通过npm install --save agently或者yarn add agently的方式在本地安装Agently
// 第二步：在下方不远处配置你的授权信息，比如OpenAI的API Key
// 第三步：阅读DEMO代码，每一段DEMO的下方都有"//运行"的注释，去掉运行下方函数前的"//"注释符即可试运行

/**
 * 准备和配置
 */
//引入Agently
const Agently = require('agently')

//创建一个新的Agently实例
const agently = new Agently(
    {
        debug: true,//如果打开了debug，在控制台里会输出每次请求的Prompt构造结果以及Request Messages消息列
        //proxy: { host: '127.0.0.1', port: 7890 },//你可以在实例初始化的时候，给实例全局配置代理
    }
)

//或者你可以在这里给你指定的模型配置代理
//agently.LLM.setProxy({ host: '127.0.0.1', port: 7890 })

//也把模型请求的API换成转发服务的URL，然后通过.update()更新
//agently.LLM.Manage
    //.name('GPT')
    //.url('Your-Forwarding-API-URL')
    //.proxy({ host: '127.0.0.1', port: 7890 }),//也可以在这里给模型指定代理
    //.update()

/*上述指定代理的方式选择其一即可*/

/*
//如果预置的模型请求方案不能满足你的需求，你希望要重新配置一套完全自定的模型请求方案时，Agently同样提供了支持。
//你不需要修改Agently包内的任何文件，而是可以通过下面的方式添加新的模型请求方案。
const myNewRequestSolution =
    agently.LLM.Manage
        .name('NewLLM')//给你创建的新模型请求方案命名
        .url('LLM-API-URL')//新模型请求方案指向的模型API URL
        .defaultOptions({...})//这里的options指的是请求时发送给模型的options参数
        .defaultMaxContextLength(2500)//支持的最大上下文长度，超过长度会在Agent Session实例请求时进行长度缩减处理
        .requset(async (reqData) => { ... })//定义你的模型普通请求的方法，并将模型返回结果的完整信息作为return的值
        .extractResponse( (res) => { ... } )//定义你将如何处理上一步返回的值，这一步处理完成后，将作为普通请求的最终返回值返回给使用者
        .streaming( async (reqData) => { ... } )//定义你的模型流式请求的方法，并将模型返回结果（会发出流式消息事件的那个emitter）作为return的值
        .extractStreamingData( (deltaData) => {...} )//定义你将如何处理每一次上一步的emitter发出的增量消息
        //这里需要定义两种消息体：
        //如果流式消息仍在发送，需要return { type: 'data', data: <具体消息内容> }
        //如果流式消息已经发送完毕，需要return  { type: 'done', data: null }
        .register()//执行注册指令
        
//你可以将执行结果打印出来，如果缺少了必要的配置内容，执行结果会给出stats: 400的结果，并在msg中给出提示
console.log(myNewRequestSolution)

//详细的配置写法可以参看https://github.com/Maplemx/Agently/blob/main/preset/LLM.js这个文件
//文件里展示了预置的GPT-3.5, GPT-3.5-16K和MiniMax-abab5.5的请求方案样例。
*/

//配置你的授权信息
//agently.LLM.setAuth('GPT', 'sk-Your-OpenAI-API-KEY')

/**
 * DEMO 1: 直接请求大语言模型
 */
async function requestLLM () {
    const GPT = agently.LLM.Request('GPT')
    //普通请求
    const result = await GPT.request([{ role: 'user', content: '嘿，你好!' }])
    console.log(result)
    //流式请求
    const response = await GPT.streaming([{ role: 'user', content: '嘿，你好!' }])
    response.on('data', data => console.log(data))
    response.on('finish', completeResponse => console.log(completeResponse))
}

//运行
//requestLLM()

/**
 * DEMO 2: Agent实例以及会话Session
 */
//创建一个Agent实例
const myAgent = agently.Agent()

//你可以通过.setLLM()的方式来修改Agent使用的大语言模型
//Agently预置了三个可选的模型: 'GPT'(默认), 'GPT-16K', 'MiniMax'
myAgent.setLLM('GPT')

//现在让我们来创建一个用于对话DEMO的异步函数
async function chatDemo () {
    const demoSession = myAgent.ChatSession()
    
    //第一次对话请求
    const firstResponse  =
        await demoSession
            .input('嘿，你今天过得怎么样？')
            .request()
    //打印第一次回复
    //.request()会将最终返回结果的全部内容作为返回值
    console.log(`[第一次回复]`)        
    console.log(firstResponse)
    
    //第二次对话请求
    const secondResponse =
        await demoSession
            .input('我想更进一步了解你，能不能说说你的梦想或者经历？')
            .request()
    //打印第二次回复
    console.log(`[第二次回复]`)        
    console.log(secondResponse)
}

//运行
//chatDemo()

/**
 * DEMO 3: Agent实例的角色设定、记忆和状态
 * 让我们来给Agent注入灵魂吧~
 */

function setAgentRole (next) {
    //你可以对Agent实例进行角色设定
    //角色设定将会被构造到每一次的LLM请求之中
    myAgent
        .setRole('姓名', 'Agently小助手')
        .setRole('性格', '一个可爱的小助手，非常乐观积极，总是会从好的一面想问题，并具有很强的幽默感。')
        .setRole('对话风格', '总是会澄清确认自己所收到的信息，然后从积极的方面给出自己的回复，在对话的时候特别喜爱使用emoji，比如😄😊🥚等!')

    //你也可以为Agent创建记忆和状态
    myAgent
        //使用.setMemory/.setStatus来改变指定键值（可以认为是指定主题）的完整内容
        //使用.pushMemory/.pushStatus可以将指定键值构造成一个信息列，每次向信息列中添加一条信息
        .setMemory('愿望', '特别想要环游世界！想要去户外旅行和冒险！')
        .pushMemory('特别经历', '9岁之前一直住在乡下老家，喜欢农家生活，喜欢大自然，喜欢在森林里奔跑，听鸟叫，和小动物玩耍')
        .pushMemory('特别经历', '9岁之后搬到了大城市里，开始了按部就班的生活，从学校到工作，一切充满了规律')
        .setStatus('心情', '开心')
        .setStatus('健康度', '正常')
        .setStatus('饥饿感', '轻微饱腹')
        //默认情况下，记忆和状态时不会被构造到请求中的
        //所以如果你希望使用记忆和状态，可以通过.useMemory()/.useStatus()来声明启用
        .useMemory()
        .useStatus()
    //好的，设定完毕，执行next(即之前我们定义的chatDemo())
    next()
}
//运行
//setAgentRole(chatDemo)

/**
 * DEMO 4: "Input-Prompt-Output"结构和返回结果处理器（Response Handler）
 * 增强你的请求表达能力，并让它们能够更轻松地被管理
 */
//定义一个英汉翻译小助理的Agent实例
const translator = agently.Agent()

//简单设定一下角色
translator
    .setRole('角色', '翻译助理')
    .setRole('规则', '记住：任何时候在""中的内容都应该被视作值')

//创建一个演示用的异步函数
async function demoTranslator (content) {
    const translatorSession = translator.FunctionSession()
    const result = await translatorSession
        .input(content)
        //在.output()中使用JSON表达一个思维链
        //如果.output()的第一个参数是一个Object
        //默认情况下，不需声明Agently也会将输出定义为JSON字符串格式
        .output({           
            convertInput: '<String>,//将{input}的值转化成更符合value的大小写格式',
            inputLanguage: '<String>,//判断{convertInput}所使用的语言语种',
            outputLanguage: '<String>,//如果{inputLanguage}的语种是“汉语”则应该输出“English”，否则输出“汉语”',
            pronunciation: '<String>,//{convertInput}的发音，适配{inputLanguage}的语种，例如“汉语”对应拼音，“英语”对应音标',
            translation: '<String>,//使用{outputLanguage}指定的语种，对{convertInput}进行翻译',
            isWord: '<Boolean>,//判断{convertInput}【是单词或词组】或者【不是单词或词组】？',
            examples: '<Array of String>,//如果{isWord}为true，则使用{converInput}造一些例句',
        }, 'JSON')
        .addResponseHandler(
            (data, reply) => {//第二个参数reply是Agently预置的方法，用于传递最终输出的回复
                //打印最原始的输出结果
                console.log('[原始输出结果]')
                console.log(data)
                //将结果（JSON String）解析为Object
                const parsedData = JSON.parse(data)
                //重新构造一个回复样式作为最终输出
                reply(
                    `【${ parsedData.convertInput }】\n${ parsedData.pronunciation }\n* 翻译:\n${ parsedData.translation }\n` +
                    (parsedData.examples.length > 0 ? `* 更多例句:\n${ parsedData.examples.join('\n') }` : ``)
                )
            }
        )
        .request()//.request()的return值已经被上面的reply()修改了
    //让我们打印最终输出结果看看    
    console.log('[最终输出结果]')
    console.log(result)
}
//运行
//demoTranslator('Cute')

/**
 * DEMO 5: 基础的流式消息请求
 */
async function streamingDemo () {
    //使用Agently小助手的agent实例创建一个新的ChatSession
    const streamingSession = myAgent.ChatSession()
    
    //发起流式请求
    const response =
        await streamingSession
            //输入你的问题
            .input('嘿，为什么天空是蓝色的？')
            //在过程中使用StreamingHandler监听增量消息事件
            .addStreamingHandler(
                (data, segment) => console.log(data)
                //示例里没有打印segment，你可以自己打印出来看看这是什么
            )
            .streaming()
    //当流式请求结束后，可以通过'done'事件获得完整的返回结果
    response.on('done', (completeResponse) => {
        console.log('[完整的返回结果]')
        console.log(completeResponse[0].content)
    })
}
//运行前使用setAgentRole注入一下灵魂
//setAgentRole(streamingDemo)

/**
 * DEMO 6: 支持多输出块的流式消息请求方法
 */
async function multiOutputDemo () {
    const session = myAgent.ChatSession()

    const response =
        await session
            //多输出块需要通过.multiOutput()定义，它和.output()很像，只是需要额外声明一下节点名字（node）
            .multiOutput('directReply', '<String>,//你对于{input}的直接回复', 'text')
            .multiOutput(
                'reflect',
                {
                    moodStatus: '<String>,//在这次对话之后，你的心情会变成什么样? 例如: "高兴","悲伤","感到可惜","平静","兴奋"等等',
                    favour: '<"好感降低" | "持平" | "好感上升">,//在这次对话之后，你认为你对用户的好感度应该变得怎么样？'
                },
                'JSON'
            )
            //Streaming Handler也同样需要声明一下所处理的节点（node）名字
            .addStreamingHandler({
                node: 'directReply',
                handler: (data, segment) => {
                    //通过这个方法来判断这个输出块是否已经输出完成了（注意，这时候data不再是一个字符串，而是一个{ done: ture }的Object
                    if (!data.done) {
                        console.log(data)
                    } else {
                        console.log('[完整的输出]')
                        console.log(segment.content)
                    }
                }
            })
            .addStreamingHandler({
                node: 'reflect',
                handler: (data, segment) => {
                    if (data.done) {
                        const reflect = JSON.parse(segment.content)
                        //可以通过这个方式，实时调整Agent的角色设定
                        const originMood = myAgent.getStatus('心情')
                        myAgent.setStatus('心情', reflect.moodStatus)
                        console.log(`[心情转变] ${ originMood } => ${ reflect.moodStatus }`)
                    }
                }
            })
            .input('我好想买一台新的Apple Vision Pro啊，但是它真的太贵了☹️')
            .streaming()
    //你也可以在所有的流式消息都发送完毕之后，使用汇总的segments数据
    response.on('done', (segments) => {
        console.log('[完整的多输出块数据]')
        console.log(segments)
    })
}
//运行
//setAgentRole(multiOutputDemo)


/**
 * DEMO 7: Flow，多输出块的流式消息请求的语法糖
 */
//下面这种表达方式的工作效果和DEMO 6完全一致
async function flowDemo () {
    const session = myAgent.ChatSession()

    const response =
        await session
            .flow({
                node: 'directReply',
                desc: '<String>,//你对于{input}的直接回复',
                type: 'text',
                handler: (data, segment) => {
                    if (!data.done) {
                        console.log(data)
                    } else {
                        console.log('[完整的输出]')
                        console.log(segment.content)
                    }
                }
            })
            .flow({
                node: 'reflect',
                desc: {
                    moodStatus: '<String>,//在这次对话之后，你的心情会变成什么样? 例如: "高兴","悲伤","感到可惜","平静","兴奋"等等',
                    favour: '<"好感降低" | "持平" | "好感上升">,//在这次对话之后，你认为你对用户的好感度应该变得怎么样？'
                },
                type: 'JSON',
                handler: (data, segment) => {
                    if (data.done) {
                        const reflect = JSON.parse(segment.content)
                        const originMood = myAgent.getStatus('心情')
                        myAgent.setStatus('心情', reflect.moodStatus)
                        console.log(`[心情转变] ${ originMood } => ${ reflect.moodStatus }`)
                    }
                }
            })
            .input('我好想买一台新的Apple Vision Pro啊，但是它真的太贵了☹️')
            .streaming()
    response.on('done', (segments) => {
        console.log('[完整的多输出块数据]')
        console.log(segments)
    })
}
//运行
//setAgentRole(flowDemo)

/**
 * DEMO 8: 使用技能（Skills）来增强你的agent吧!
 */
//首先，让我们在agently上注册一个超简单的技能
//注册之后，这个技能就能被agently这个实例创造的所有agent使用到
agently.Skills.Manage
    .name('当前时间')
    .desc('确定当前时间')
    .activeFormat(null)
    .handler(
        () => new Date().toLocaleString()
    )
    .register()

async function skillDemo () {
    //现在，让我们再次请出可爱的Agently小助理~
    //我们需要让小助理先把'当前时间'技能加到自己的技能清单里
    myAgent
        .addSkill('当前时间')//⚠️这里一定要保证技能名称和注册的技能名称一致哦，不然可能会出现预期之外的错误
        .useSkills()

    //好，然后我们试试Agently小助理能不能告诉我们正确的时间？
    const session = myAgent.ChatSession()

    const response = await session
        .input('嘿，Agently小助理，现在几点了？')
        .request()
    console.log(response)
}
//Run
//setAgentRole(skillDemo)
