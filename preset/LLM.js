const EventEmitter = require('events'),
      axios = require('axios-https-proxy-fix')

module.exports = (Agently) => {
    //OpenAI GPT 3.5 turbo 4k
    Agently.LLM.Manage
        //Model Name
        .name('GPT')
        //API URL
        .url('https://api.openai.com/v1/chat/completions')
        //Default Options
        .defaultOptions({
            model: 'gpt-3.5-turbo',
            temperature: 0.8,
        })
        //Default Max Context Length (Limited by model runtime tokens limitation)
        .defaultMaxContextLength(2500)
        //Request Method
        .request(
            async (reqData) => {
                let data = { ...reqData.options } || {}
                data.model = data.model || 'gpt-3.5-turbo'
                data.messages = reqData.messages
                data.stream = false
                const result = await axios.request({
                    url: reqData.url,
                    method: 'POST',
                    data: data,
                    headers: { 
                        'Authorization': `Bearer ${ reqData.auth }`,
                        'Content-Type': 'application/json',
                    },
                    dataType: 'json',
                    proxy:
                        reqData.proxy?.host && reqData.proxy?.port
                        ? {
                            host: reqData.proxy.host,
                            port: reqData.proxy.port,
                          }
                        : undefined
                })
                return result.data
            }
        )
        //Extract response data
        .extractResponse(
            res => res.data.choices[0].message.content
        )
        //Request in streaming way
        .streaming(
            async (reqData) => {
                let data = { ...reqData.options } || {}
                data.model = data.model || 'gpt-3.5-turbo'
                data.messages = reqData.messages
                data.stream = true
                const result = await axios.request({
                    url: reqData.url,
                    method: 'POST',
                    data: data,
                    headers: { 
                        'Authorization': `Bearer ${ reqData.auth }`,
                        'Content-Type': 'application/json',
                    },
                    dataType: 'json',
                    responseType: 'stream',
                    proxy:
                        reqData.proxy?.host && reqData.proxy?.port
                        ? {
                            host: reqData.proxy.host,
                            port: reqData.proxy.port,
                          }
                        : undefined
                })
                return result.data
            }
        )
        //Extract streaming data
        //when streaming is still on: return { type: 'data', data: <choices 0 content> } 
        //when streaming is done: return { type: 'done', data: null }
        .extractStreamingData(
            data => {
                if (data && data !== '[DONE]\n\n') {
                    try {
                        return { type: 'data', data: JSON.parse(data)?.choices[0] || '' }
                    } catch (e) {
                        console.error(e)
                    }
                } else {
                    return { type: 'done', data: null }
                }
            }
        )
        .register()

    //OpenAI GPT 3.5 turbo 16k
    Agently.LLM.Manage
        //Model Name
        .name('GPT-16K')
        //API URL
        .url('https://api.openai.com/v1/chat/completions')
        //Default Options
        .defaultOptions({
            model: 'gpt-3.5-turbo-16k',
            temperature: 0.8,
        })
        //Default Max Context Length (Limited by model runtime tokens limitation)
        .defaultMaxContextLength(13500)
        //Request Method
        .request(
            async (reqData) => {
                let data = { ...reqData.options } || {}
                data.model = data.model || 'gpt-3.5-turbo-16k'
                data.messages = reqData.messages
                data.stream = false
                const result = await axios.request({
                    url: reqData.url,
                    method: 'POST',
                    data: data,
                    headers: { 
                        'Authorization': `Bearer ${ reqData.auth }`,
                        'Content-Type': 'application/json',
                    },
                    dataType: 'json',
                    proxy:
                        reqData.proxy?.host && reqData.proxy?.port
                        ? {
                            host: reqData.proxy.host,
                            port: reqData.proxy.port,
                          }
                        : undefined
                })
                return result.data
            }
        )
        //Extract response data
        .extractResponse(
            res => res.data.choices[0].message.content
        )
        //Request in streaming way
        .streaming(
            async (reqData) => {
                let data = { ...reqData.options } || {}
                data.model = data.model || 'gpt-3.5-turbo-16k'
                data.messages = reqData.messages
                data.stream = true
                const result = await axios.request({
                    url: reqData.url,
                    method: 'POST',
                    data: data,
                    headers: { 
                        'Authorization': `Bearer ${ reqData.auth }`,
                        'Content-Type': 'application/json',
                    },
                    dataType: 'json',
                    responseType: 'stream',
                    proxy:
                        reqData.proxy?.host && reqData.proxy?.port
                        ? {
                            host: reqData.proxy.host,
                            port: reqData.proxy.port,
                          }
                        : undefined
                })
                return result.data
            }
        )
        //Extract streaming data
        //when streaming is still on: return { type: 'data', data: <choices 0 content> } 
        //when streaming is done: return { type: 'done', data: null }
        .extractStreamingData(
            data => {
                if (data !== '[DONE]\n\n') {
                    return { type: 'data', data: JSON.parse(data).choices[0] }
                } else {
                    return { type: 'done', data: null }
                }
            }
        )
        .register()

    //MiniMax (default model: abab5.5-chat)
    Agently.LLM.Manage
        //Model Name
        .name('MiniMax')
        //API URL
        .url('https://api.minimax.chat/v1/text/chatcompletion')
        //Default Options
        .defaultOptions({
            model: 'abab5-chat',
            tokens_to_generate: 3000,
            temperature: 0.8,
        })
        //Request Method
        .request(
            async (reqData) => {
                let data = { ...reqData.options } || {}
                data.model = data.model || 'abab5-chat'
                data.stream = false
                //Split SYSTEM messages to prompt
                let prompt = ''
                data.messages = []
                for (let i = 0; i < reqData.messages.length; i++) {
                    if (reqData.messages[i]['sender_type'] === 'SYSTEM') {
                        prompt += `${ reqData.messages[i].text }\n`
                    } else {
                        data.messages.push(reqData.messages[i])
                    }
                }
                if (prompt !== '') {
                    data.prompt = prompt
                    data.role_meta = {
                        user_name: reqData.userName || 'USER',
                        bot_name: reqData.botName || 'BOT',
                    }
                }
                const result = await axios.request({
                    url: `${ reqData.url }?GroupId=${ reqData.auth.groupId }`,
                    method: 'POST',
                    data: data,
                    headers: {
                        'Authorization': `Bearer ${ reqData.auth.apiKey }`,
                        'Content-Type': 'application/json',
                    },
                    dataType: 'json',
                })
                return result.data
            }
        )
        //Extract response data
        .extractResponse(
            res => (
                res.data.choices
                ? res.data.choices[0].text
                : `Error: ${ JSON.stringify(res.data.base_resp.status_msg) }`
            )
        )
        //Request in streaming way
        .streaming(
            async (reqData) => {
                let data = { ...reqData.options } || {}
                data.model = 'abab5.5-chat'
                data.stream = true
                data.use_standard_sse = false
                //Split SYSTEM messages from messages and put it into prompt
                let prompt = ''
                data.messages = []
                for (let i = 0; i < reqData.messages.length; i++) {
                    if (reqData.messages[i]['sender_type'] === 'SYSTEM') {
                        prompt += `${ reqData.messages[i].text }\n`
                    } else {
                        data.messages.push(reqData.messages[i])
                    }
                }
                if (prompt !== '') {
                    data.prompt = prompt
                    data.role_meta = {
                        user_name: reqData.userName || 'USER',
                        bot_name: reqData.botName || 'BOT',
                    }
                }
                const result = await axios.request({
                    url: `${ reqData.url }?GroupId=${ reqData.auth.groupId }`,
                    method: 'POST',
                    data: data,
                    headers: {
                        'Authorization': `Bearer ${ reqData.auth.apiKey }`,
                        'Content-Type': 'application/json',
                    },
                    dataType: 'json',
                    responseType: 'stream',
                })
                return result.data
            }
        )
        //Extract streaming data
        //when streaming is still on: return { type: 'data', data: <choices 0 content> } 
        //when streaming is done: return { type: 'done', data: null }
        .extractStreamingData(
            data => {
                data = JSON.parse(data)
                if (data.reply && data.choices[0].delta === '') {
                    return { type: 'done', data: null }
                } else {
                    data.choices[0].delta = { content: data.choices[0].delta }
                    return { type: 'data', data: data.choices[0] }
                }
            }
        )
        //If model required messages queue format is not the same as GPT messages queue,
        //we need to define how to transform the messages into the format model need.
        .transformMessages(
            messages => {
                if (!(messages instanceof Array)) messages = [messages]
                const roleDict = {
                    'system': 'SYSTEM',
                    'user': 'USER',
                    'assistant': 'BOT',
                }    
                return messages.map(
                    item => {
                        return { sender_type: roleDict[item.role.toLowerCase()], text: item.content }
                    }
                )
            }
        )
        .register()

        //Set default LLM in a new agent
        Agently.Options.set('defaultAgentSettings.llmName', 'GPT')
}