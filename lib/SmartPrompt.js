function isDict (obj) {
    return Object.prototype.toString.call(obj) === '[object Object]'
}

function tab (layer) {
    let content = ''
    for (let i = 0; i < layer; i++) {
        content += '\t'
    }
    return content
}

class Generator {
    static generateInstructMessage (instructDict) {
        let content = ''
        for (let key in instructDict) {
            let explanation =
                typeof(instructDict[key]) === 'string'
                || typeof(instructDict[key]) === 'number'
                ? instructDict[key]
                : JSON.stringify(instructDict[key])
            content += `${ key.toUpperCase() }: ${ explanation }\n`
        }
        return content ? [{ role: 'system', content: content }] : []
    }

    static generatePromptContent (promptDesc, inputDesc, formatDesc) {
        let content = ''
        //Generate Instruct(Prompt)
        if (promptDesc) {
            if (typeof(promptDesc) === 'string') {
                content += `[INSTRUCT]\n${ promptDesc }\n`
            } else if (isDict(promptDesc)) {
                content += `[INSTRUCT]\n`
                for (let key in promptDesc) {
                    let explanation =
                        typeof(promptDesc[key]) === 'string'
                        || typeof(promptDesc[key]) === 'number'
                        ? promptDesc[key]
                        : JSON.stringify(promptDesc[key])
                    content += `${ key.toUpperCase() }: ${ explanation }\n`
                }
            }
        }
        //Generate Input
        if (inputDesc) {
            if (typeof(inputDesc) === 'string') {
                content += `[INPUT]\n${ inputDesc }\n`
            } else if (isDict(inputDesc)) {
                content += `[INPUT]input\n`
                for (let key in inputDesc) {
                    let explanation =
                        /*typeof(inputDesc[key]) === 'string'
                        || typeof(inputDesc[key]) === 'number'
                        ? inputDesc[key]
                        :*/ JSON.stringify(inputDesc[key])
                    content += `.${ key }: ${ explanation }\n`
                }
            }
        }
        //Generate Format
        if (formatDesc) {
            if (typeof(formatDesc) === 'string') {
                content += `[OUTPUT FORMAT]\n${ formatDesc }\n`
            } else if (isDict(formatDesc)) {
                content += `[OUTPUT FORMAT]\n${ Generator.generateThinkAndSay(formatDesc) }\n`
            }
        }
        content += `[OUTPUT]\n`
        return content
    }

    static generateJSONFormat (formatDict, layer = 0) {
        if (isDict(formatDict)) {
            let content = ''
            if (layer > 0) content += '\n'
            content += `${ tab(layer) }{\n`
            for (let key in formatDict) {
                content += `${ tab(layer + 1) }"${ key }": ${ Generator.generateJSONFormat(formatDict[key], layer + 1) }\n`
            }
            content += `${ tab(layer) }},`
            return content
        } else {
            return typeof(formatDict) === 'string'
                   || typeof(formatDict) === 'number'
                   ? formatDict
                   : JSON.stringify(formatDict)
        }
    }

    static generateThinkAndSay (formatDict, layer = 0) {
        let content = ''
        if (formatDict.reply) {
            content += `STRUCTURE:\n\`\`\`\n<Reply Part>\n<Break Line Part>\n<JSON Part>\n\`\`\`\n\n`
            content += `REQUIREMENT of <Reply Part>:\n${ formatDict.reply }\n`
            content += `REQUIREMENT of <Break Line Part>:\nMUST USE ">>>---BREAKLINE---<<<"!\n`
            const { reply, ...formatDictWithoutReply } = formatDict
            content += `REQUIREMENT of <JSON Part>:\ntype:JSON\nformat definition:\n${ Generator.generateJSONFormat(formatDictWithoutReply) }\n`
            content += `recheck:Make sure output JSON can be parsed by Python and NodeJS without decorations and spaces!`
        } else {
            return this.generateJSONFormat(formatDict)
        }
        return content
    }

    static generateSmartContent (guideDesc, inputDesc, formatDesc) {
        let content = ''
        //Generate Input
        if (inputDesc) {
            if (typeof(inputDesc) === 'string') {
                content += `[INPUT]\n${ inputDesc }\n`
            } else if (isDict(inputDesc)) {
                content += `[INPUT]\ninput\n`
                for (let key in inputDesc) {
                    let explanation =
                        /*typeof(inputDesc[key]) === 'string'
                        || typeof(inputDesc[key]) === 'number'
                        ? inputDesc[key]
                        :*/ JSON.stringify(inputDesc[key])
                    content += `.${ key }: ${ explanation },\n`
                }
            }
        }

        //Generate Instruct(Guide || Prompt)
        if (guideDesc) {
            if (typeof(guideDesc) === 'string') {
                content += `[INSTRUCT]\n${ guideDesc }\n`
            } else if (isDict(guideDesc)) {
                content += `[INSTRUCT]\n`
                for (let key in guideDesc) {
                    let explanation =
                        typeof(guideDesc[key]) === 'string'
                        || typeof(guideDesc[key]) === 'number'
                        ? guideDesc[key]
                        : JSON.stringify(guideDesc[key])
                    content += `${ key.toUpperCase() }: ${ explanation }\n`
                }
            }
        }

        //Generate Format
        if (formatDesc) {
            if (typeof(formatDesc) === 'string') {
                content += `[OUTPUT FORMAT]\n${ formatDesc }\n`
                content += `[OUTPUT]\n`
            } else if (isDict(formatDesc)) {
                content += `[OUTPUT FORMAT]\nTYPE: JSON\nFORMAT DEFINITION:\n${ Generator.generateJSONFormat(formatDesc) }\n`
                //content += `[OUTPUT FORMAT]\n${ Generator.generateThinkAndSay(formatDesc) }\n`
                content += `[RECHECK]\nMake sure output JSON can be parsed by Python and NodeJS without decorations and spaces!\n\n`
                content += `[OUTPUT]\noutput = `
            }
        }        
        return content
    }
}

/*console.log(Generator.generateJSONFormat({
    target: '<String>,//User target',
    language: '<CN | EN>,//User input\'s language',
    result: {
        translation: '<String>,//Translation Result',
        examples: '<Array>,//Examples using {result.translation}'
    },
    reply: '<String>,//Your final reply',
    extraInfo: ['1. You are an assistant.', '2. You can not give any answer that you are not sure.']
}))*/

class DirectAsk {
    constructor (SmartAgent) {
        this.LLM = SmartAgent.LLM
        this.Memory = SmartAgent.Memory
        this.Options = SmartAgent.Options
        this.runtime = {}
        this._reset()
    }

    _reset () {
        this.runtime = {
            useMemory: false,
            remember: false,
            userInput: '',
        }
    }

    useMemory (isUseMemory) {
        this.runtime.useMemory = isUseMemory
        return this
    }

    remember (isRemember) {
        this.runtime.remember = isRemember
        return this
    }

    addMemory (memoryFragment) {
        this.Memory.addMemory(memoryFragment)
        return this
    }

    instruct (key, value) {
        this.Memory.setInstruct(key, value)
        return this
    }

    ask (userInput) {
        this.runtime.userInput = userInput
        return this
    }

    async start () {
        let requestMessages = []
        //Instruct
        if (this.Options.get('language')) this.instruct('output language', languageName)
        if (this.Options.get('knowTime')) this.instruct('Current Time', new Date().toLocaleString())
        requestMessages = requestMessages.concat(
            Generator.generateInstructMessage(
                this.Memory.getInstruct()
            )
        )
        //Memory
        if (this.runtime.useMemory) requestMessages = requestMessages.concat(await this.Memory.getMemory())
        //New Message
        requestMessages.push({ role: 'user', content: this.runtime.userInput })
        //Request
        const result = await this.LLM.request(requestMessages)
        //Remember
        if (this.runtime.remember) this.Memory.addMemory([
            { role: 'user', content: this.runtime.userInput },
            result.message
        ])
        this._reset()
        return result
    }
}

class BasicPrompt {
    constructor (SmartAgent) {
        this.LLM = SmartAgent.LLM
        this.Memory = SmartAgent.Memory
        this.runtime = {}
        this.Options = SmartAgent.Options
        this._reset()
    }

    _reset () {
        this.runtime = {
            useMemory: false,
            remember: false,
            promptDesc: undefined,
            inputDesc: undefined,
            formatDesc: undefined,
            returnPrompt: false,
        }
    }

    useMemory (isUseMemory) {
        this.runtime.useMemory = isUseMemory
        return this
    }

    remember (isRemember) {
        this.runtime.remember = isRemember
        return this
    }

    addMemory (memoryFragment) {
        this.Memory.addMemory(memoryFragment)
        return this
    }

    instruct (key, value) {
        this.Memory.setInstruct(key, value)
        return this
    }

    prompt (promptDesc) {
        this.runtime.promptDesc = promptDesc
        return this
    }

    input (inputDesc) {
        this.runtime.inputDesc = inputDesc
        return this
    }

    format (formatDesc) {
        this.runtime.formatDesc = formatDesc
        return this
    }

    async start () {
        let requestMessages = []
        //Instruct
        if (this.Options.get('language')) this.instruct('output language', languageName)
        if (this.Options.get('knowTime')) this.instruct('Current Time', new Date().toLocaleString())
        requestMessages = requestMessages.concat(
            Generator.generateInstructMessage(
                this.Memory.getInstruct()
            )
        )
        //Memory
        if (this.runtime.useMemory) requestMessages = requestMessages.concat(await this.Memory.getMemory())
        //New Message
        const promptContent = Generator.generatePromptContent(
                  this.runtime.promptDesc,
                  this.runtime.inputDesc,
                  this.runtime.formatDesc
              )
        requestMessages.push({
            role: 'user',
            content: promptContent
        })
        if (this.runtime.returnPrompt) {
            return {
                prompt: promptContent,
                requestMessages: requestMessages,
            }
        }
        //Request
        const result = await this.LLM.request(requestMessages)
        //Remember
        if (this.runtime.remember) this.Memory.addMemory([
            { role: 'user', content: promptContent },
            result.message
        ])
        this._reset()
        return result
    }

    async returnPrompt () {
        this.runtime.returnPrompt = true
        return await this.start()
    }
}

class SmartPrompt {
    constructor (SmartAgent) {
        this.LLM = SmartAgent.LLM
        this.Memory = SmartAgent.Memory
        this.runtime = {}
        this.Options = SmartAgent.Options
        this._reset()
    }

    _reset () {
        this.runtime = {
            useMemory: false,
            remember: false,
            guideDesc: undefined,
            inputDesc: undefined,
            formatDesc: {},
            result: {},
            resultHandlers: [],
            reply: undefined,
            returnContent: false,
            returnPrompt: false,
        }
    }

    //Basic Methods
    useMemory (isUseMemory) {
        this.runtime.useMemory = isUseMemory
        return this
    }

    remember (isRemember) {
        this.runtime.remember = isRemember
        return this
    }

    addMemory (memoryFragment) {
        this.Memory.addMemory(memoryFragment)
        return this
    }

    instruct (key, value) {
        this.Memory.setInstruct(key, value)
        return this
    }

    prompt (guideDesc) {
        return this.guide(guideDesc)
    }

    guide (guideDesc) {
        this.runtime.guideDesc = guideDesc
        return this
    }

    input (inputDesc) {
        this.runtime.inputDesc = inputDesc
        return this
    }

    inJSON (formatDict) {
        for (let key in formatDict) {
            this.runtime.formatDesc[key] = formatDict[key]
        }
        return this
    }

    addResultHandler (handler) {
        this.runtime.resultHandlers.push(handler)
        return this
    }

    changeInstruct (resultKeys, instructKey) {
        const that = this
        this.addResultHandler(
            (result) => {
                if (typeof(resultKeys) === 'string') resultKeys = [resultKeys]
                that.Memory.setInstruct(
                    instructKey,
                    JSON.stringify(resultKeys.map(
                        (item) => result[item]
                    ))
                )
            }
        )
        return this
    }

    changeMemo (resultKeys, memoKey) {
        const that = this
        this.addResultHandler(
            (result) => {
                if (typeof(resultKeys) === 'string') resultKeys = [resultKeys]
                that.Memory.setMemo(
                    memoKey,
                    JSON.stringify(resultKeys.map(
                        (item) => result[item]
                    ))
                )
            }
        )
        return this
    }

    reply (resultHandler) {
        const that = this
        this.addResultHandler(
            async (result) => {
                if (resultHandler === undefined) {
                    that.runtime.reply = result
                } else {
                    if (typeof(resultHandler) === 'string') resultHandler = [resultHandler]
                    if (resultHandler instanceof Array) {
                        that.runtime.reply = resultHandler.map(
                            (item) => result[item]
                        ).join('\n')
                    } else if (typeof(resultHandler) === 'function'){
                        that.runtime.reply = await resultHandler(result)
                    }
                }
            }
        )
        return this
    }

    async _requestForJSON (requestMessages, retryTimes = 0) {
        try {
            const result = await this.LLM.request(requestMessages)
            return JSON.parse(result.message.content)
        } catch (e) {
            if (retryTimes < this.Options.get('retryTimes')) {
                if (this.Options.get('debug')){
                    console.log('[JSON Parse Failed]')
                    console.log(e.message)
                }
                retryTimes++
                const intervalId = setInterval(function() {
                    clearInterval(intervalId);
                }, this.Options.get('retryWait'))
                return await this._requestForJSON(requestMessages, retryTimes)
            } else {
                if (this.Options.get('debug')){
                    console.log('[JSON Parse Failed]')
                    console.log(e.message)
                }
                return { error: 'Can not parse.' }
            }
        }
    }

    async start () {
        let requestMessages = []
        //Instruct
        if (this.Options.get('language')) this.instruct('output language', languageName)
        if (this.Options.get('knowTime')) this.instruct('Current Time', new Date().toLocaleString())
        requestMessages = requestMessages.concat(
            Generator.generateInstructMessage(
                this.Memory.getInstruct()
            )
        )
        //Memory
        if (this.runtime.useMemory) requestMessages = requestMessages.concat(await this.Memory.getMemory())
        //New Message
        const promptContent = Generator.generateSmartContent(
                  this.runtime.guideDesc,
                  this.runtime.inputDesc,
                  this.runtime.formatDesc
              )
        requestMessages.push({
            role: 'user',
            content: promptContent
        })
        if (this.runtime.returnPrompt) {
            return {
                prompt: promptContent,
                requestMessages: requestMessages,
            }
        }
        //Request
        this.runtime.result = await this._requestForJSON(requestMessages)
        //Handle Result
        for (let i = 0; i < this.runtime.resultHandlers.length; i++) {
            const handlerResult = await this.runtime.resultHandlers[i](this.runtime.result)
            if (handlerResult && handlerResult.key && handlerResult.value) {
                this.runtime.result[handlerResult.key] = handlerResult.value
            }
        }
        //Confirm Reply
        const replyMessage = {
            role: 'assistant',
            content: 
                typeof(this.runtime.reply) === 'string'
                || typeof(this.runtime.reply) === 'number'
                ? this.runtime.reply
                : JSON.stringify(this.runtime.reply)
        }
        //Remember
        if (this.runtime.remember) this.Memory.addMemory([
            {
                role: 'user',
                content: 
                    typeof(this.runtime.inputDesc) === 'string'
                    || typeof(this.runtime.inputDesc) === 'number'
                    ? this.runtime.inputDesc
                    : JSON.stringify(this.runtime.inputDesc)
            },
            replyMessage
        ])
        const finalReply = this.runtime.returnContent ? this.runtime.reply : replyMessage
        this._reset()
        if (this.Options.get('debug')) {
            console.log(`[Final Response]`)
            console.log(replyMessage)
        }
        return finalReply
    }

    async returnContent () {
        this.runtime.returnContent = true
        this.reply()
        return await this.start()
    }
}

exports.Direct = DirectAsk
exports.Prompt = BasicPrompt
exports.Smart = SmartPrompt