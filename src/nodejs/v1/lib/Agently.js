const Options = require('./Options'),
      LLM = require('./LLM'),
      Agent = require('./Agent'),
      Skills = require('./Skills'),
      ProcessUnit = require('./ProcessUnit')

class Agently {
    constructor (options, ...presets) {
        this.debug = (content) => { if (this.Options.get('debug')) console.log(content) }
        this.Options = new Options(options)
        this.LLM = new LLM(this)
        this.Agent = (agentSettings) => new Agent(agentSettings, this)
        this.Skills = new Skills(this)
        this.ProcessUnit = new ProcessUnit(this)
        this.use = (presetHandler) => { presetHandler(this) }
        for (let i = 0; i < presets.length; i++) {
            this.use(presets[i])
        }
    }
}

module.exports = Agently