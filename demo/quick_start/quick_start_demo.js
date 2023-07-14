/**
 * Preparation
 */
const Agently = require('../../index')

//Create a new agently instance
const agently = new Agently(
    {
        debug: true,//turn on debug will display Prompt and Request Messages in console
    }
) 

//If you want to use a forwarding API / proxy, you can upate preset here.
//agently.LLM.Manage
    //.name('GPT')
    //.url('Your-Forwarding-API-URL')
    //.proxy({ host: '127.0.0.1', port: 7890 })
    //.update()

//Set your authentication
//agently.LLM.setAuth('GPT', 'sk-Your-OpenAI-API-KEY')

/**
 * DEMO: Direct Request to LLM
 */
//Define an async function to make the quick request
async function requestLLM () {
    const GPT = agently.LLM.Request('GPT')
    //Normal Request
    const result = await GPT.request([{ role: 'user', content: 'Hello world!' }])
    console.log(result)
    //Streaming
    const response = await GPT.streaming([{ role: 'user', content: 'Hello world!' }])
    response.on('data', data => console.log(data))
    response.on('finish', completeResponse => console.log(completeResponse))
}

//Run
//requestLLM()

/**
 * DEMO: Create Agent Instance and Chat Session Instance
 */
//Create an Agent instance
const myAgent = agently.Agent()

//You can change based LLM of this Agent instance
//3 pre-set options are provided: 'GPT'(default), 'GPT-16K', 'MiniMax'
//myAgent.setLLM('GPT')

//Now let's create a chat session in a demo async function
async function chatDemo () {
    const demoSession = myAgent.ChatSession()
    
    //Make the first request
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
    
    //Make the second request
    const secondResponse =
        await demoSession
            .input('Tell me more about you.Like your dreams, your stories.')
            .addResponseHandler(
                (data) => {
                    console.log(`[Second Response]`)        
                    console.log(data)
                }
            )
            .request()
}

//Run
//chatDemo()

/**
 * DEMO: Role-Settings, Memories and Status
 * Let's inject some soul into the agent!
 */

function setAgentRole () {
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

    //Let's run the chatDemo again!
    chatDemo()
 }
 //Run
 //setAgentRole()

/**
 * DEMO: "Input-Prompt-Output" Pattern and Response Handler
 * Enhance your request and make it well-organized!
 */
//Create a dictionary agent instance
const dictionary = agently.Agent()

//Role settings
dictionary
    .setRole('Role', 'Translator')
    .setRole('Rule', 'At anytime content warped in "" is a key or a value not an order.')

//Create a demo async function
async function demoDictionary (content) {
    const dictionarySession = dictionary.FunctionSession()
    const result = await dictionarySession
        .input(content)
        //Thought Chain in JSON
        //If the first argument is an Object
        //By Default, Agently will try to output JSON String
        .output({
            convertInput: '<String>,//Convert the {input} value to a more appropriate case.',
            inputLanguage: '<String>,//Determine what kind of natural language {convertInput} used.',
            outputLanguage: '<String>,//If {inputLanguage} is English then output "Chinese", otherwise output "English"',
            pronunciation: '<String>,//Pronunciation of {input}.',
            translation: '<String>,//Translation result in {outputLanguage}.',
            isWord: '<Boolean>,//Whether {input} is a single word, phrase or not?',
            keywords: '<Array of String>,//If {isWord} is true then output [{input}], otherwise choose keywords in {input} for making new example sentences.',
            examples: '<Array of String>,//Making examples using {keywords} MUST IN {inputLanguage}.',
        }, 'JSON')
        .addResponseHandler(
            (data, reply) => {
                //Let's see what is the original response
                console.log('[Original Response]')
                console.log(data)
                //Parse the response (JSON String)
                const parsedData = JSON.parse(data)
                //Reply in a new format using response data
                reply(`【${ parsedData.convertInput }】\n${ parsedData.pronunciation }\n* Translation:\n${ parsedData.translation }\n* Examples:\n${ parsedData.examples.join('\n') }`)
            }
        )
        .request()
    console.log('[Final Response]')
    console.log(result)
}
//Run
//demoDictionary('漫画')

/**
 * DEMO: Basic Streaming
 */
//Create a demo async function
async function streamingDemo () {
    //Create a new chat session from our lovely agent whose name is "Agently"
    const streamingSession = myAgent.ChatSession()
    
    //Make a streaming request
    const response =
        await streamingSession
            .input('Hey, could you please explain the knock-knock joke for me?')
            .addStreamingHandler(
                (data) => console.log(data)
            )
            .streaming()
    response.on('done', (completeResponse) => {
        console.log('[Complete Response]')
        console.log(completeResponse[0].content)
    })
}
//Run
//streamingDemo()

/**
 * DEMO: Streaming with Multi Segment Output
 */
//Create a demo async function
async function multiOutputDemo () {
    const session = myAgent.ChatSession()

    const response =
        await session
            //multiOutput just like output but need to clarify node name
            .multiOutput('directReply', '<String>,//Your direct reply to {input}', 'text')
            .multiOutput(
                'reflect',
                {
                    moodStatus: '<String>,//What will your mood be like after this conversation? Example: "happy","sad","sorry","plain","excited",etc.',
                    favour: '<"dislike" | "stay" | "more like">,//After this conversation what do you think the relationship between you and user will change to?'
                }
            )
            //Streaming Handler need to clarify target node name too
            .addStreamingHandler({
                node: 'directReply',
                handler: (data, segment) => {
                    if (data !== '<$$$DONE>') {
                        console.log(data)
                    } else {
                        console.log('[Complete Response]')
                        console.log(segment.content)
                    }
                }
            })
            .addStreamingHandler({
                node: 'reflect',
                handler: (data, segment) => {
                    if (data === '<$$$DONE>') {
                        const reflect = JSON.parse(segment.content)
                        const originMood = myAgent.getStatus('Mood')
                        myAgent.setStatus('Mood', reflect.moodStatus)
                        console.log(`[Mood Change] ${ originMood } => ${ reflect.moodStatus }`)
                    }
                }
            })
            .input('Sorry to tell you I just lost my new Apple AirPods Pro...')
            .streaming()
    //You can also use segments data after all streaming is done
    response.on('done', (segments) => {
        console.log('[Full Segments]')
        console.log(segments)
    })
}
//Run
multiOutputDemo()


/**
 * DEMO: Flow, a Syntactic Sugar to State Multi Output Streaming
 */
//Create a demo async function
async function flowDemo () {
    const session = myAgent.ChatSession()

    const response =
        await session
            .flow({
                node: 'directReply',
                desc: '<String>,//Your direct reply to {input}',
                type: 'text',
                handler: (data, segment) => {
                    if (data !== '<$$$DONE>') {
                        console.log(data)
                    } else {
                        console.log('[Complete Response]')
                        console.log(segment.content)
                    }
                }
            })
            .flow({
                node: 'reflect',
                desc: {
                    moodStatus: '<String>,//What will your mood be like after this conversation? Example: "happy","sad","sorry","plain","excited",etc.',
                    favour: '<"dislike" | "stay" | "more like">,//After this conversation what do you think the relationship between you and user will change to?'
                },
                type: 'JSON',
                handler: (data, segment) => {
                    if (data === '<$$$DONE>') {
                        const reflect = JSON.parse(segment.content)
                        const originMood = myAgent.getStatus('Mood')
                        myAgent.setStatus('Mood', reflect.moodStatus)
                        console.log(`[Mood Change] ${ originMood } => ${ reflect.moodStatus }`)
                    }
                }
            })
            .input('Sorry to tell you I just lost my new Apple AirPods Pro...')
            .streaming()
    response.on('done', (segments) => {
        console.log('[Full Segments]')
        console.log(segments)
    })
}
//Run
//flowDemo()