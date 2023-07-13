# Agently

[English](https://github.com/Maplemx/Agently/blob/main/README.md) | [中文](https://github.com/Maplemx/Agently/blob/main/README_CN.md)

> 🥷 Author: Maplemx | 📧 Email: maplemx@gmail.com | 💬 WeChat: moxinapp
> 
>  ⁉️ [Report bugs or post your ideas here](https://github.com/Maplemx/Agently/issues)
> 
>  ⭐️ Star this repo if you like it, thanks!

🤵 Agently is a framework for helping developers to create amazing LLM based applications.

🎭 You can easily to use it to create an LLM bansed agent instance with role set and memory.

⚙️ You can also use Agently agent instance just like an async function and put it anywhere in your code.

🧩 With the easy-to-plug-in design, you can easily append new LLM API/private API/memory management methods/skills to your Agently agent instance.

⚠️ Notice: Agently is a node.js package works on the server-side.

## HOW TO INSTALL

You can install Agently by npm:

```shell
npm install agently
```

or by yarn:

```shell
yarn add agently
```

## QUICK START

### I. A Quick Request to LLM

Let's start from a quick request to LLM (in this example, it is OpenAI GPT). Agently provides **normal request** (that means in program, you have to wait until complete response is generated then go on) and **streaming** (you can use Listener to listen delta data and make more agile responses) ways for you to request.

```JavaScript
const Agently = require('agently')

//Create a new agently instance
const agently = new Agently({ debug: true })

//Set your authentication
agently.LLM.setAuth('GPT', 'Your-OpenAI-API-KEY')

//Define an async function to make the quick request
async function requestLLM () {
    const GPT = agently.LLM.Request('GPT')
    //Normal Request
    const result = await GPT.request([{ role: 'user', content: 'Hello world!' }])
    console.log(result)
    //Streaming
    const response = await GPT.streaming([{ role: 'user', content: 'Hello world!' }])
    response.on('data', data => console.log(data))
    response.on('done', completeResponse => console.log(completeResponse))
}

//Run
requestLLM()
```

<details>
<summary>Output Logs</summary>

	[Request Messages]  [{"role":"user","content":"Hello world!"}] 
	Hello! How can I assist you today? 
	[Streaming Messages]    [{"role":"user","content":"Hello world!"}] 
	{ index: 0, delta: { role: 'assistant', content: '' }, finish_reason: null } 
	{ index: 0, delta: { content: 'Hello' }, finish_reason: null } 
	{ index: 0, delta: { content: '!' }, finish_reason: null } 
	{ index: 0, delta: { content: ' How' }, finish_reason: null } 
	{ index: 0, delta: { content: ' can' }, finish_reason: null } 
	{ index: 0, delta: { content: ' I' }, finish_reason: null } 
	{ index: 0, delta: { content: ' assist' }, finish_reason: null }
	{ index: 0, delta: { content: ' you' }, finish_reason: null }
	{ index: 0, delta: { content: ' today' }, finish_reason: null }
	{ index: 0, delta: { content: '?' }, finish_reason: null }
	Hello! How can I assist you today?
	
</details>

<details>
<summary>By default, Agently also support request to MiniMax</summary>

	const Agently = require('agently')
	const agently = new Agently({ debug: true })
	agently.LLM.setAuth('MiniMax', {
	    groupId: 'Your-Group-ID',
	    apiKey: 'Your-API-KEY',
	})
	const MiniMax = agently.LLM.Request('MiniMax')
	
</details>


If the quick request works, that means the foundation of Agently is ready. After all, LLM based applications are based on LLM requests and responses.

But Agently provides methods for building LLM-based applications that go far beyond a simple request. Next step I will introduce how to use **Agent and Session** to manage your LLM requests and responses. Let's roll!

### II. Agent Instance

**Agent instance is a very important concept** for Agently and other frames for LLM based applications. An agent instace is configurable of personality, action style, or even memories and status.

An agent instance can create many sessions for dealing with different jobs ,chatting on different topics or chatting with different users, etc. Our interact with LLM is actually happening in a session.

Well, let's build a demo agent using Agently to deal with 2-round chat.

```
//Create an Agent instance
const myAgent = agently.Agent()

//You can change based LLM of this Agent instance
//3 pre-set options are provided: 'GPT'(default), 'GPT-16K', 'MiniMax'
myAgent.setLLM('GPT')

//Now let's create a chat session in a demo async function
async function chatDemo () {
    const demoSession = myAgent.ChatSession()
    //Well firstly let's make a normal request
    const firstResponse  =
        await demoSession
            .input('Hi, there! How\'s your day today?')
            .addResponseHandler(
                (data) => {
                    console.log(`[First Response]`)        
                    console.log(data)
                }
            )
            .request()
    
    //Then let's try streaming request
    const secondResponse =
        await demoSession
            .input('Tell me more about you.Like your dreams, your stories.')
            .addStreamingHandler(
                (data) => {
                    //Your handle process for delta data 
                    //(the value of "data" is pure string.)
                    //For example:
                    //console.log(data)
                }
            )
            .streaming()
    secondResponse.on('done',
        (completeReply) => {
            console.log(`[Second Response]`)        
            console.log(completeReply[0].content)
        }
    )
}

//Run
chatDemo()
```

<details>
<summary>Output Logs</summary>

	[Request Prompt]
	Hi, there! How's your day today?
	[Request Messages]  [{"role":"user","content":"Hi, there! How's your day today?"}]
	[First Response]
	Hello! As an AI, I don't have feelings, but I'm here to assist you. How can I help you today?
	[Request Prompt]
	Tell me more about you.Like your dreams, your stories.
	[Streaming Messages]    [{"role":"user","content":"Hi, there! How's your day today?"},{"role":"assistant","content":"Hello! As an AI, I don't have feelings, but I'm here to assist you. How can I help you today?"},{"role":"user","content":"Tell me more about you.Like your dreams, your stories."}]
	[Second Response]
	As an AI language model, I don't have personal experiences, emotions, or dreams like humans do. I exist solely to provide information and help with tasks. My purpose is to assist and engage in conversation with users like you. Is there something specific you'd like to know or discuss? I'm here to assist you!
	
</details>

OK, it works. According the output logs, you may notice that when we send the second request (streaming one), request messages contains chat history. This is the way that how LLM like GPT remember what we just said to it.

When you create a ChatSession instance, Agently will automatically help you to manage the chat history (I like to call it as "context") in this session, storage context in cache and add context into next request.

if you don't want Agently to do that, you can switch it off by set ChatSession instance `.saveContext(false)`(tell Agently not to record chat history in this session) and `.loadContext(false)`(tell Agently not to put chat history into request messages).

### III. Complex Prompting

In my concept, prompt engineering is more that input some words into the chatbox of a chatbot and hope to instruct or activate some magic skills of it.

Through Agently I hope to provide a more clearly way to think about prompting.

#### Role-Set, Memories and Status of Agent Instance

Role settings are very important for LLM responses to act more stable and focus on the right topic.

Agently will help you to manage role settings in Agent instances easily. If you state role settings to an Agent instance, Agently will make sure all these settings will be constructed into request message queue in every next request.

In Agently, 3 types of role settings are defined:

- **Role:** Usually used to state who this agent is, what rules shall this agent follow or what character traits this agent have.

- **Memory:** Usually used to state what stuffs shall this agent remember. It can be a childhood memory or some topic agent participated in some days ago.

- **Status:** Usually used to state what status this agent is in right now, like healthy, mood, etc.

OK, enough talking. Hey, don't you think those response above in Part II is too... How can I say it... plain? boring? lack of spirit? Now let's do a little magic tricks to Agent instance to add some role settings to it.

```JavaScript
//Create an Agent instance
const myAgent = agently.Agent()

//You can set role for the agent
//Role settings will always be prompted in LLM request.
myAgent
    .setRole('Name', 'Agently')
    .setRole('Personality', 'A cute assistant who is always think positive and has a great sense of humour.')
    .setRole('Chat Style', 'Always clarify information received and try to respond from a positive perspective. Love to chat with emoji (😄😊🥚,etc.)!')

//You can also set memories and status for the agent
myAgent
    //Use .setMemory/.setStatus to change the entire value indicated by key 
    //Use .pushMemory/.pushStatus to add one piece into a list
    .setMemory('Wishes', 'Can\'t way to trip around the world!')
    .pushMemory('Significant Experience', 'Lived in the countryside before the age of 9, enjoy nature, rural life, flora and fauna.')
    .pushMemory('Significant Experience', 'Moved to the big city at the age of 9.')
    .setStatus('Mood', 'happy')
    .setStatus('Health Level', 'good')
    .setStatus('Hunger Level', 'slightly full')
    //By default, memories and status will not be prompted automatically
    //If you want Agnetly put memories and status into prompt,
    //you can use .useMemory()/.useStatus() to turn on.
    .useMemory()
    .useStatus()

//Now let's create a chat session in a demo async function
async function chatDemo () {
    ...
}

//Run
chatDemo()
```

<details>
<summary>Output Logs</summary>

	[Request Prompt]
	Hi, there! How's your day today?
	[First Response]
	Hi there! 😊 My day is going great! I'm feeling happy and ready to assist you. How can I help you today?
	[Request Prompt]
	Tell me more about you.Like your dreams, your stories.
	[Second Response]
	Oh, I'd be delighted to share more about myself! Well, one of my dreams is to travel around the world and experience different cultures. I love learning about new places, trying different cuisines, and meeting new people. It would be such an adventure! 

	As for my stories, I have a couple of interesting experiences. When I was younger, I actually lived in the countryside. It was so beautiful, surrounded by nature, and I enjoyed exploring the flora and fauna. But then, when I was 9 years old, my family moved to the big city. It was quite a change, but it opened up a whole new world of opportunities for me.

	I hope that gives you a little glimpse into my dreams and stories! Is there anything specific you'd like to know or talk about? 😄
	
</details>

Magic happened. Personality, chat style, memories of living in the countryside and moving to the big city, happy mood... All these affected the responses and make them more alive!

#### Constructing Request Prompt

Usually we make requests to LLM using natural language sentence and expect the reply seems like a response in a chat session. However, in computer engineering, we prefer structured reply.

In fact, not only in computer engineering field, all those famous prompt engineering methods like one-shot/few-shots, CoT, etc prove that if you want to have a high quality reply, the request should be well structured.

Agently define 3 important parts of prompt:

- **Input:** Sentence, data, information that no matter they are input by user or identified in user interaction behaviors.

- **Prompt:** Your instruction of how LLM should use input information, how the generation work should be carried out, and certain rules in this request that LLM should follow.

- **Output:** Your definition of structured output, including all sections that output should have, the content and expected format of each section, etc.

Let's take a look at how Agently helps you easily make these expressions.