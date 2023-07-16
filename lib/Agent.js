const { v4: uuidv4 } = require('uuid')



class AgentSession {
    constructor (sessionSettings, Agent) {
        const self = this
        this.id = uuidv4()
        this.context = {
            full: [],
            request: [],
        }

        this.debug = (content) => { if (this.sessionSettings.debug) Agent.debug(content) }

        this.agentSettings = Agent.agentSettings
        this.getAgentSettings = () => Agent.agentSettings
        this.getMemories = Agent.getMemories
        this.getMemory = Agent.getMemory
        this.getStatus = Agent.getStatus

        this.sessionSettings = {
            loadContext: this.agentSettings.loadSessionContext || true,
            saveContext: this.agentSettings.saveSessionContext || true,
            maxContextLength: this.agentSettings.maxContextLength || 3000,
            debug: this.agentSettings.debug || false,
        }
        sessionSettings = sessionSettings || {}
        for (let key in sessionSettings) {
            this.sessionSettings[key] = sessionSettings[key]
        }
        this.getSessionSettings = () => self.sessionSettings

        this.prompt = {}
        this.getPrompt = () => self.prompt
        this.responseHandlers = []
        this.getResponseHandlers = () => self.responseHandlers
        this.streamingHandlers = []
        this.getStreamingHandlers = () => self.streamingHandlers
        this.runtime = {}
        this.initRuntime()

        this.Request = Agent.ProcessUnit.Request(this)
    }

    setDebug (isDebug) {
        this.sessionSettings.debug = isDebug
        return this
    }

    initRuntime () {
        this.prompt = {
            input: undefined,
            prompt: [],
            output: undefined,
            multiOutput: [],
        }

        this.responseHandlers = []
        this.streamingHandlers = []

        this.runtime = {}
    }

    //Manage Context
    setLoadContext (isLoadContext) {
        this.sessionSettings.loadSessionsContext = isLoadContext
        return this
    }

    setSaveContext (isSaveContext) {
        this.sessionSettings.saveSessionsContext = isSaveContext
        return this
    }

    setMaxContextLength (maxContextLength) {
        this.sessionSettings.maxContextLength = maxContextLength
        return this
    }

    appendContext (contextMessages) {
        if (!(contextMessages instanceof Array)) contextMessages = [contextMessages]
        this.context.full = this.context.full.concat(contextMessages)
        this.context.request = this.context.request.concat(contextMessages)
        return this
    }

    coverContext (contextMessages) {
        contextMessages = contextMessages || []
        if (!(contextMessages instanceof Array)) contextMessages = [contextMessages]
        this.context.full = contextMessages
        this.context.request = contextMessages
        return this
    }

    //Prompt
    input (inputDesc) {
        this.prompt.input = inputDesc
        //console.log(this.prompt)
        return this
    }

    prompt (title, content) {
        this.prompt.prompt.push({ title: title, content: content })
        return this
    }

    output (desc, type) {
        this.prompt.output = { desc: desc, type: type }
        return this
    }

    multiOutput (title, desc, type) {
        type = type || (Object.prototype.toString.call(desc) === '[object Object]') ? 'JSON' : 'text'
        this.prompt.multiOutput.push({ title: title, desc: desc, type: type })
        return this
    }

    //Handle Response
    addResponseHandler (responseHandler) {
        if (responseHandler) this.responseHandlers.push(responseHandler)
        return this
    }

    //Handle Streaming
    addStreamingHandler (streamingHandler) {
        if (streamingHandler) {
            if (streamingHandler.node) {
                this.streamingHandlers.push(streamingHandler)
            } else {
                this.streamingHandlers.push({
                    node: null,
                    handler: streamingHandler
                })
            }
        }
        return this
    }

    //Streaming Flow Syntactic Sugar
    flow (flowDesc) {
        flowDesc = {
            node: flowDesc.node || uuidv4(),
            desc: flowDesc.desc,
            type: flowDesc.type || (Object.prototype.toString.call(flowDesc.desc) === '[object Object]') ? 'JSON' : 'text',
            handler: flowDesc.handler,
        }
        this.multiOutput(flowDesc.node, flowDesc.desc, flowDesc.type)
        if (flowDesc.handler) this.addStreamingHandler({ node: flowDesc.node, handler: flowDesc.handler })
        return this
    }

    //Start Request
    async request() {
        const response = await this.Request.start('request')
        this.initRuntime()
        return response
    }

    async streaming() {
        const response = await this.Request.start('streaming')
        return response
    }
}

class Agent {
    constructor
     (agentSettings, Agently) {
        const self = this
        this.Options = Agently.Options
        this.debug = Agently.debug
        this.LLM = Agently.LLM
        this.ProcessUnit = Agently.ProcessUnit

        this.agentSettings = {
            role: {},
            skills: [],
            useSkills: false,
            useMemory: false,
            useStatus: false,
            loadSessionContext: true,
            saveSessionContext: true,
            debug: this.Options.get('debug') || false,
        }
        const defaultAgentSettings = this.Options.get('defaultAgentSettings') || {}
        for (let key in defaultAgentSettings) {
            this.agentSettings[key] = defaultAgentSettings[key]
        }
        agentSettings = agentSettings || {}
        if (typeof(agentSettings) === 'string') {
            this.setLLM(agentSettings)
            agentSettings = {}
        }
        for (let key in agentSettings) {
            this.agentSettings[key] = agentSettings[key]
        }
        if (this.agentSettings.llmName) this.setLLM(this.agentSettings.llmName)
        this.getAgentSettings = () => self.agentSettings

        this.memories = {}
        this.getMemories = () => self.memories
        this.getMemory = (key) => self.memories[key]
        
        this.status = {}
        this.getStatus = (key) => {
            key = key || ''
            const splitedKey = key.split('.')
            let result = self.status
            for (let i = 0; i < splitedKey.length; i++) {
                if (splitedKey[i] && splitedKey[i] !== '') result = result[splitedKey[i]]
                if (!result) return undefined
            }
            return result
        }

        this.addSkill = (skillName) => {
            if (self.agentSettings.skills.indexOf(skillName) === -1) self.agentSettings.skills.push(skillName)
            return this
        }
        this.removeSkill = (skillName) => {
            const index = self.agentSettings.skills.indexOf(skillName)
            if (index > -1) self.agentSettings.splice(index, 1)
            return this
        }

        this.Session = (sessionSettings) => new AgentSession(sessionSettings, this)
        this.ChatSession = () => this.Session()
        this.FunctionSession = () => this.Session({ loadSessionContext: false, saveSessionContext: false })
    }

    setDebug (isDebug) {
        this.agentSettings.debug = isDebug
        return this
    }

    setLLM (llmName) {
        this.agentSettings.llmName = llmName
        this.agentSettings.maxContextLength = this.LLM.llmList[llmName].defaultMaxContextLength || 3000
        return this
    }

    setRequestOptions (requestOptions) {
        this.agentSettings.requestOptions = requestOptions
        return this
    }

    setMaxContentLength (maxContextLength) {
        this.agentSettings.maxContextLength = maxContextLength
        return this
    }

    setRole (key, value) {
        if (!value) {
            value = key
            key = 'role'
        }
        this.agentSettings.role[key] = value
        return this
    }

    useSkills (isUseSkills = true) {
        this.agentSettings.useSkills = isUseSkills
        return this
    }
    
    useMemory (isUseMemory = true) {
        this.agentSettings.useMemory = isUseMemory
        return this
    }

    setMemory (key, value) {
        this.memories[key] = value
        return this
    }

    pushMemory (key, value) {
        if (!(this.memories[key] instanceof Array)) this.memories[key] = this.memories[key] ? [this.memories[key]] : []
        if (this.memories[key].indexOf(value) === -1) this.memories[key].push(value)
        return this
    }

    removeMemory (key, value) {
        if (this.memories[key]) {
            if (this.memories[key] instanceof Array) {
                const targetIndex = this.memories[key].indexOf(value)
                if (value === true) {
                    this.memories[key] = []
                } else if ( targetIndex >= 0) {
                    this.memories[key].splice(targetIndex, 1)
                }
            } else {
                if (value === true) this.memories[key] = null
            }
        }
        return this
    }

    useStatus (isUseStatus = true) {
        this.agentSettings.useStatus = isUseStatus
        return this
    }

    setStatus (key, value) {
        if (!key) return false
        const splitedKey = key.split('.')
        let current = this.status
        for (let i = 0; i < splitedKey.length - 1; i++) {
            if (splitedKey[i] && splitedKey[i] !== '' && !current[splitedKey[i]]) {
                current[splitedKey[i]] = {}
            }
            current = current[splitedKey[i]]
        }
        current[splitedKey[splitedKey.length - 1]] = value
        return this
    }

    useSkills (isUseSkills = true) {
        this.agentSettings.useSkills = isUseSkills
        return this
    }
}

module.exports = Agent