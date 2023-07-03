const axios = require('axios-https-proxy-fix')
/**
 * req in request(req):
 * {
    * messages: <Array> messages mappinged by .requestMapping
    * url: <String> LLM API url,
    * auth: <Dict> authorization dict
    * options: <Dict> all parameters pass to LLM API (default value is set by .options)
    * proxy: <Dict> { host: 'xxx.xxx.xxx.xxx', port: 0000 } if needed.
 * }
 */
module.exports = {
    'GPT': {
        url: 'https://api.openai.com/v1/chat/completions',
        request: async (req) => {
            let data = req.options || {}
            data.model = data.model || 'gpt-3.5-turbo'
            data.messages = req.messages
            const result = await axios.request({
                url: req.url,
                method: 'POST',
                data: data,
                headers: { 
                    'Authorization': `Bearer ${ req.auth.apiKey }`,
                    'Content-Type': 'application/json',
                },
                dataType: 'json',
                proxy:
                    req.proxy?.host && req.proxy?.port
                    ? {
                        host: req.proxy.host,
                        port: req.proxy.port,
                      }
                    : undefined
            })
            return result.data
        },
        options: {
            model: 'gpt-3.5-turbo',
            temperature: 0.8,
        },
        requestMapping: undefined,
        responseMapping: (response) => {
            return {
                role: response.choices[0].message.role,
                content: response.choices[0].message.content,
            }
        },
    },
    'MiniMax': {
        url: 'https://api.minimax.chat/v1/text/chatcompletion',
        request: async (req) => {
            let data = req.options || {}
            //Format Instruct for MiniMax
            data.messages = []
            let prompt = ''
            for (let i = 0; i < req.messages.length; i++) {
                if (req.messages[i]['sender_type'] === 'SYSTEM') {
                    prompt += `${ req.messages[i].text }\n`
                } else {
                    data.messages.push(req.messages[i])
                }
            }
            if (prompt !== '') {
                data.prompt = prompt
                data.role_meta = {
                    user_name: 'user',
                    bot_name: 'assistant'
                }
            }
            const result = await axios.request({
                url: `${ req.url }?GroupId=${ req.auth.groupId }`,
                method: 'POST',
                data: data,
                headers: {
                    'Authorization': `Bearer ${ req.auth.apiKey }`,
                    'Content-Type': 'application/json',
                },
                dataType: 'json',
            })
            return result.data
        },
        options: {
            model: 'abab5-chat',
            tokens_to_generate: 1500,
            temperature: 0.8,
        },
        requestMapping (requestMessages) {
            return requestMessages.map(
                (item) => {
                    let sender_type = ''
                    switch (item.role) {
                        case 'system':
                            sender_type = 'SYSTEM'
                            break
                        case 'user':
                            sender_type = 'USER'
                            break
                        case 'assistant':
                        default:
                            sender_type = 'BOT'
                            break
                    }
                    return { sender_type: sender_type, text: item.content }
                }
            )
        },
        responseMapping (response) {
            return (response.choices
                ? { role: 'assistant', content: response.choices[0].text }
                : { role: 'assistant', content: `🤖出错了：${ JSON.stringify(response.base_resp) }` }
                )
        }
    }
}