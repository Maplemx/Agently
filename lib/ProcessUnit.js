const EventEmitter = require('events')

class PrefixManage {
    constructor (ProcessUnit) {
        this.prefix = ProcessUnit.prefix
        this.debug = ProcessUnit.debug
        this.runtime = {}
    }

    generateRole (generateRoleHandler) {
        this.runtime.generateRole = generateRoleHandler
        return this
    }

    generateStatus (generateStatusHandler) {
        this.runtime.generateStatus = generateStatusHandler
        return this
    }

    generateMemories (generateMemoriesHandler) {
        this.runtime.generateMemories = generateMemoriesHandler
        return this
    }    

    generateSkills (generateSkillsHandler) {
        this.runtime.generateSkills = generateSkillsHandler
        return this
    }

    generateContext (generateContextHandler) {
        this.runtime.generateContext = generateContextHandler
        return this
    }

    shortenContext (shortenContextHandler) {
        this.runtime.shortenContext = shortenContextHandler
        return this
    }

    generatePrompt (generatePromptHandler) {
        this.runtime.generatePrompt = generatePromptHandler
        return this
    }

    register () {
        let missing = []
        if (!this.runtime.generateRole) missing.push('generateRole')
        if (!this.runtime.generateContext) missing.push('generateContext')
        if (!this.runtime.shortenContext) missing.push('shortenContext')
        if (!this.runtime.generatePrompt) missing.push('generatePrompt')
        if (missing.length === 0) {
            this.prefix.default = { ...this.runtime }
            this.runtime = {}
            return { status: 200 }
        } else {
            const msg = `[Prefix Register] Failed: missing ${ JSON.stringify(missing) }`
            this.debug(msg)
            return { status: 400, msg: msg }
        }
    }

    update () {
        for (let key in this.runtime) {
            this.prefix.default[key] = this.runtime[key]
        }
        this.runtime = {}
        return { status: 200 }
    }
}

class ProcessRequest {
    constructor (AgentSession, LLM, Skills, ProcessUnit) {
        this.Skills = Skills
        this.sessionId = AgentSession.id
        this.agentSettings = AgentSession.agentSettings
        this.sessionSettings = AgentSession.sessionSettings
        this.memories = {
            memories: AgentSession.memories,
            getMemory: AgentSession.getMemory,
        }
        this.status = {
            status: AgentSession.status,
            getStatus: AgentSession.getStatus,
        }
        this.context = AgentSession.context
        this.appendContext = AgentSession.appendContext
        this.prompt = AgentSession.prompt
        this.runtime = AgentSession.runtime
        this.prefix = ProcessUnit.prefix.default
        this.responseHandlers = AgentSession.responseHandlers
        this.streamingHandlers = AgentSession.streamingHandlers
        this.responseSkills = AgentSession.responseSkills
        this.initRuntime = AgentSession.initRuntime
        this.debug = AgentSession.debug
        this.llmRequest = LLM.Request(this.agentSettings.llmName)
    }

    async start(requestType) {
        let requestMessages = []
        //Generate Role Messages
        if (this.agentSettings.role.length > 0) {
            requestMessages = requestMessages.concat(this.prefix.generateRole(this.agentSettings.role))
        }
        //Generate Status Messages
        if (this.agentSettings.useStatus && this.prefix.generateStatus) {
            requestMessages = requestMessages.concat(this.prefix.generateStatus(this.status))
        }
        //Generate Memories Messages
        if (this.agentSettings.useMemory && this.prefix.generateMemories) {
            requestMessages = requestMessages.concat(this.prefix.generateMemories(this.memories))
        }
        //Generate Skills Messages
        if (this.agentSettings.useSkills && this.prefix.generateSkills) {
            requestMessages = requestMessages.concat(this.prefix.generateSkills(this.agentSettings.skills))
        }
        if (this.sessionSettings.loadContext) {
            //Generate Context Messages
            let contextMessages = this.prefix.generateContext(this.context)
            //Shorten Context
            if (JSON.stringify(contextMessages).length > this.sessionSettings.maxContextLength) {
                contextMessages = await this.prefix.shortenContext(contextMessages, this.context.full, this.sessionSettings.maxContextLength)
            }
            this.context.request = contextMessages
            requestMessages = requestMessages.concat(contextMessages)
        }
        //Generate Request Prompt
        const promptMessage = this.prefix.generatePrompt(this.prompt)
        this.debug(promptMessage.content)
        requestMessages = requestMessages.concat(promptMessage)
        //Request LLM
        const response = await this.llmRequest[requestType](requestMessages, this.agentSettings.requestOptions || {})
        //Handle Response
        //<direct request>
        if (requestType === 'request') {
            //Call Handlers
            for (let i = 0; i < this.responseHandlers.length; i++) {
                this.responseHandlers[i](response, (content) => { this.runtime.reply = content })
            }
            //Save Context
            const finalResponse = this.runtime.reply || response
            if (finalResponse) {
                this.appendContext([
                    promptMessage,
                    { role: 'assistant', content: finalResponse }
                ])
            }
            //Init Runtime
            this.initRuntime()
            //Final Response
            return finalResponse
        //<streaming>
        } else if (requestType === 'streaming') {
            //Create response event listerners
            const responseEvent = new EventEmitter()
            for (let i = 0; i < this.streamingHandlers.length; i++) {
                responseEvent.on(this.streamingHandlers[i].node || 'data', this.streamingHandlers[i].handler || this.streamingHandlers[i])
            }
            let buffer = '',
                isInSegment = false,
                currentNode = '',
                segment = { node: null, content: '' },
                segments = []
            response.on('data', (data) => {
                const delta = data.delta.content
                if (typeof(delta) === 'string') {
                    //Single Output
                    if (this.prompt.multiOutput.length === 0) {
                        segment.content += delta
                        responseEvent.emit('data', delta, segment)
                        segments.push(segment)
                    //Multi Output
                    } else {
                        buffer += delta
                        if (!isInSegment) {
                            const startMarkSearcher = buffer.match(/<\$\$\$node=.+>/ig)
                            if (startMarkSearcher && startMarkSearcher.length > 0){
                                currentNode = startMarkSearcher[0].substr(9)
                                currentNode = currentNode.substr(0, currentNode.length - 1)
                                buffer = buffer.replace(/[\s\S]*<\$\$\$node=.+>/ig, '')
                                segment.node = currentNode
                                segment.content = buffer
                                responseEvent.emit(currentNode, buffer, segment)
                                buffer = ''
                                isInSegment = true
                            }
                        } else {
                            if (Math.sign(buffer.indexOf('<')) + Math.sign(buffer.indexOf('<\/')) + Math.sign(buffer.indexOf('<\/$')) + Math.sign(buffer.indexOf('<\/$$')) + Math.sign(buffer.indexOf('<\/$$$')) + Math.sign(buffer.indexOf('<\/$$$>')) > -6) {
                                const content = buffer.substr(0, buffer.indexOf('<'))
                                if (content.length > 0) {
                                    segment.content += content
                                    responseEvent.emit(currentNode, content, segment)
                                }
                                buffer = buffer.substr(buffer.indexOf('<'), buffer.length)
                                if (buffer.length >= 6 && buffer.substr(0, 6) !== '<\/$$$>') {
                                    segment.content += buffer
                                    responseEvent.emit(currentNode, buffer, segment)
                                    buffer = ''
                                } else {
                                    buffer = buffer.replace('<\/$$$>')
                                    responseEvent.emit(currentNode, '<$$$DONE>', segment)
                                    segments.push({...segment})
                                    isInSegment = false
                                }
                            } else {
                                segment.content += delta
                                responseEvent.emit(currentNode, delta, segment)
                                buffer = ''
                            }
                        }
                    }
                }
            })
            response.on('done', () => {
                response.emit('segments', segments)
            })
            return response
        }
    }
}

class ProcessUnit {
    constructor (Agently) {
        this.Options = Agently.Options
        this.debug = Agently.debug
        this.prefix = {}
        this.Manage = new PrefixManage(this)
        this.Request = (AgentSession) => new ProcessRequest(AgentSession, Agently.LLM, Agently.Skills, this)
    }
}

module.exports = ProcessUnit