const LLM_PRESET = require('./LLM_PRESET')

class LLM {
    constructor (SmartAgent) {
        this.llmName = SmartAgent.llmName
        this.url = LLM_PRESET[this.llmName]?.url
        this.requestLLM = LLM_PRESET[this.llmName]?.request
        this.LLMOptions = LLM_PRESET[this.llmName]?.options || {}
        this.requestMapping = LLM_PRESET[this.llmName]?.requestMapping
        this.responseMapping = LLM_PRESET[this.llmName]?.responseMapping
        this.Options = SmartAgent.Options
        /*this.auth = SmartAgent.options?.auth || {}
        this.proxy = {
            host: undefined,
            port: undefined,
        }
        this.retryTimes = SmartAgent.options?.retryTimes || 3
        this.retryWait = SmartAgent.options?.retryWait || 2000
        this.debug = SmartAgent.options?.debug || false*/
    }

    setUrl (url) {
        this.url = url
        return this
    }

    setRequest (request) {
        this.requestLLM = request
        return this
    }

    setOption (key, value) {
        this.LLMOptions[key] = value
        return this
    }

    setRequestMapping (handler) {
        this.requestMapping = handler
        return this
    }

    setResponseMapping (handler) {
        this.responseMapping = handler
        return this
    }

    async _request (req, retryTimes = 0) {
        try {
            const response = await this.requestLLM({
                messages: req.messages,
                url: req.url,
                auth: req.auth,
                options: req.options,
                proxy: req.proxy,
            })
            return {
                status: 200,
                message: this.responseMapping
                    ? this.responseMapping(response)
                    : response
            }
        } catch (e) {
            if (this.debug) console.log(`[REQUEST LLM FAILED]\tLLM Name: ${ this.llmName }\tError: ${ JSON.stringify(e.message) }\tRequest: ${ JSON.stringify(req) }\t RetryTimes: ${ retryTimes }/${ this.retryTimes }`)
            if (retryTimes < this.retryTimes) {
                retryTimes++
                const intervalId = setInterval(function() {
                    clearInterval(intervalId);
                }, this.retryWait)
                return await this._request(req, retryTimes)
            } else {
                return {
                    status: 400,
                    message: { role: 'system', content: `🧐出错了: ${ JSON.stringify(e.message) }` }
                }
            }
        }
    }

    async request (messages) {
        //Mapping Request Messages
        messages =
            this.requestMapping
            ? this.requestMapping(messages)
            : messages
        if (this.Options.get('debug')) {
            console.log(`[Request Messages]`)
            console.log(messages)
        }
        const result = await this._request({
                messages: messages,
                url: this.url,
                auth: this.Options.get('auth'),
                options: this.LLMOptions,
                proxy: this.Options.get('proxy'),
            })        
        if (this.Options.get('debug')) {
            console.log(`[Response Message]`)
            console.log(result )
        }
        return result
    }
}

module.exports = LLM