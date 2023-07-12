const Agently = require('./lib/Agently'),
      presetLLM = require('./preset/LLM'),
      prefix = require('./preset/prefix')

class PresetAgently extends Agently {
    constructor (options) {
        super(options, presetLLM, prefix)
    }
}

module.exports = PresetAgently