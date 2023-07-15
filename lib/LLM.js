const EventEmitter = require('events')

class LLMManage {
    constructor (LLM) {
        this.llmList = LLM.llmList
        this.debug = LLM.debug
        this.runtime = {}
    }

    name (llmName) {
        this.runtime.name = llmName
        return this
    }

    url (apiUrl) {
        this.runtime.url = apiUrl
        return this
    }

    defaultOptions (defaultOptions) {
        this.runtime.defaultOptions = defaultOptions
        return this
    }

    defaultMaxContextLength (defaultMaxContextLength) {
        this.runtime.defaultMaxContextLength = defaultMaxContextLength
        return this
    }

    request (requestMethod) {
        this.runtime.request = requestMethod
        return this
    }

    extractResponse (extractResponseHandler) {
        this.runtime.extractResponse = extractResponseHandler
        return this
    }

    streaming (streamingMethod) {
        this.runtime.streaming = streamingMethod
        return this
    }

    extractStreamingData (extractStreamingDataHandler) {
        this.runtime.extractStreamingData = extractStreamingDataHandler
        return this
    }

    transformMessages (transformMessagesHandler) {
        this.runtime.transformMessages = transformMessagesHandler
        return this
    }

    register () {
        let missing = []
        if (!this.runtime.name) missing.push('name')
        if (!this.runtime.url) missing.push('url')
        if (!this.runtime.request && !this.runtime.streaming) missing.push('request or streaming')
        if (missing.length === 0) {
            this.llmList[this.runtime.name] = { ...this.runtime }
            this.runtime = {}
            return { status: 200 }
        } else {
            const msg = `[LLM Register] Failed: missing ${ JSON.stringify(missing) }`
            this.debug(msg)
            this.runtime = {}
            return { status: 400, msg: msg }
        }
    }

    update () {
        if (!this.runtime.name) {
            const msg = `[LLM Update] Failed: Update require model name`
            this.debug(msg)
            return { status: 400, msg: msg }
        }
        if (!this.llmList[this.runtime.name]) {
            const msg = `[LLM Update] Failed: Can not find model "${ this.runtime.name }"`
            this.debug(msg)
            return { status: 400, msg: msg }
        }
        for (let key in this.runtime) {
            this.llmList[this.runtime.name][key] = this.runtime[key]
        }
        this.runtime = {}
        return { status: 200 }
    }
}

class LLMRequest {
    constructor (llmName, LLM) {
        this.debug = LLM.debug
        this.Options = LLM.Options
        this.llm = LLM.llmList[llmName]
        this.auth = undefined
        this.proxy = undefined
        this.retryTimes = this.Options.get('retryTimes')
        this.retryPause = this.Options.get('retryPause')
    }

    setAuth (auth) {
        this.auth = auth
        return this
    }

    setProxy (proxy) {
        this.proxy = proxy
        return this
    }

    setRetryTimes (retryTimes) {
        this.retryTimes = retryTimes
        return this
    }

    setRetryPause (retryPause) {
        this.retryPause = retryPause
        return this
    }

    async _request (messages, options, type) {
        let methodName, transform, request, extract
        //Request method with retry
        const __request = (request, reqData, retryTimes = 1) => {
            return new Promise(
                async (resolve, reject) => {
                    try {
                        const response = await request(reqData)
                        resolve({
                            status: 200,
                            data: response,
                        })
                    } catch (e) {
                        this.debug(`[Request Failed]\tLLM Name: ${ this.llm.name }\tError: ${ JSON.stringify(e.message) }\tRequest Data: ${ JSON.stringify(reqData) }\tRetry Times: ${ retryTimes }/${ this.retryTimes }\t Pause: ${ this.retryPause }`)
                        if (retryTimes < this.retryTimes) {
                            retryTimes++
                            setTimeout( async () => {
                                const result = await __request(request, reqData, retryTimes)
                                resolve(result)
                            }, this.retryPause)
                        } else {
                            return {
                                status: 400,
                                msg: e.message
                            }
                        }
                    }
                }
            )
        }

        if (type === 'request') {
            //Check if request is existed
            if (!this.llm.request) {
                const msg = `[Request Failed]\tLLM Name: ${ this.llm.name }\tError: requestMethod is not registered.`
                this.debug(msg)
                return { status: 400, msg: msg }
            }
            methodName = 'Request'
            transform = this.llm.transformMessages
            request = this.llm.request
            extract = this.llm.extractResponse
        } else if (type === 'streaming') {
            //Check if streamMethod is existed
            if (!this.llm.streaming) {
                const msg = `[Streaming Failed]\tLLM Name: ${ this.llm.name }\tError: streaming is not registered.`
                this.debug(msg)
                return { status: 400, msg: msg }
            }
            methodName = 'Streaming'
            transform = this.llm.transformMessages
            request = this.llm.streaming
            extract = this.llm.extractStreamingData
        }
        
        //Generate request options
        let requestOptions = this.llm.defaultOptions
        if (options) {
            for (let key in options) {
                requestOptions[key] = options[key]
            }
        }
        //Request with retry
        messages = transform ? transform(messages) : messages
        this.debug(`[${ methodName } Messages]\t${ JSON.stringify(messages) }`)
        const responseResult = await __request(
            request,
            {
                messages: messages,
                url: this.llm.url,
                options: requestOptions,
                auth: this.auth || this.llm.auth || this.Options.get('auth')[this.llm.name] || '',
                proxy: this.proxy || this.llm.proxy || this.Options.get('proxy') || undefined,
            }
        )
        if (type === 'request') {
            //Extract response result
            const finalResult =
                extract
                ? extract(responseResult)
                : responseResult.data
            return finalResult
        } else if (type === 'streaming') {
            //Extract stream data
            const finalResult = new EventEmitter()
            let streamingBuffer = '',
                role = ''
            responseResult.data.on('data', data => {
                const extractResult = 
                    extract
                    ? extract(data.toString().slice(6))
                    : JSON.parse(data.toString().slice(6))
                if (!extractResult.type) extractResult = { type: 'data', data: extractResult }
                const sendResult = {
                    type: extractResult.type,
                    data: extractResult.data,
                }
                if (sendResult.type !== 'done') {
                    if (typeof(sendResult?.data?.delta?.role) === 'string') role = sendResult?.data.delta.role
                    if (typeof(sendResult?.data?.delta?.content) === 'string') {
                        const delta = sendResult.data.delta.content
                        streamingBuffer += delta
                        if (delta.length > 10) {
                            for (let i = 0; i < delta.length; i += 10) {
                                let tempResult = { 
                                    type: sendResult.type,
                                    data: sendResult.data,
                                }
                                tempResult.data.delta.content = delta.substr(i, 10)
                                finalResult.emit(tempResult.type, tempResult.data)
                            }
                        } else {
                            finalResult.emit(sendResult.type, sendResult.data)
                        }
                    }
                } else {
                    finalResult.emit('finish', { role: role, content: streamingBuffer })
                }
            })
            return finalResult
        }
    }

    async request (messages, options) {
        return await this._request(messages, options, 'request')
    }

    async streaming (messages, options) {
        return await this._request(messages, options, 'streaming')
    }
}

class LLM {
    constructor (Agently) {
        this.Options = Agently.Options
        this.debug = Agently.debug
        this.llmList = {}
        this.Manage = new LLMManage(this)
        this.Request = (llmName) => new LLMRequest(llmName, this)
    }

    setAuth (llmName, auth)
     {
        if (this.llmList[llmName]) {
            this.llmList[llmName].auth = auth
        } else {
            this.llmList[llmName] = { auth: auth }
        }
        return this
    }

    setProxy (llmName, proxy) {
        if (this.llmList[llmName]) {
            this.llmList[llmName].proxy = proxy
        } else {
            this.llmList[llmName] = { proxy: proxy }
        }
        return this
    }
}

module.exports = LLM