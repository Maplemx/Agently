const Options = require('./Options'),
      LLM = require('./LLM'),
      Memory = require('./Memory'),
      SmartPrompt = require('./SmartPrompt'),
      Tools = require('./Tools')


class Agently {
    constructor (llmName, options) {
        this.llmName = llmName
        this.Options = new Options(options)
        this.LLM = new LLM(this)
        this.Memory = new Memory(this)
        this.Direct = new SmartPrompt.Direct(this)
        this.Prompt = new SmartPrompt.Prompt(this)
        this.Smart = new SmartPrompt.Smart(this)
        this.Tools = new Tools(this)
    }

    setOption (key, value) {
        this.Options.set(key, value)
        return this
    }

    getOption (key) {
        return this.Options.get(key)
    }

    addMemory (memoryFragment) {
        this.Memory.addMemory(memoryFragment)
        return this
    }

    instruct (key, value) {
        this.Memory.setInstruct(key, value)
        return this
    }

    memo (key, value) {
        this.Memory.setMemo(key, value)
        return this
    }

    language (languageName) {
        this.Options.set('language', languageName)
        return this
    }

    debug (isDebug) {
        this.Options.set('debug', isDebug)
        return this
    }
}

module.exports = Agently