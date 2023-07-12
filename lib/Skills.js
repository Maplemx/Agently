class SkillsManage {
    constructor (Skills) {
        this.skillList = Skills.skillList
        this.debug = Skills.debug
        this.runtime = {}
    }

    name (skillName) {
        this.runtime.name = skillName
        return this
    }

    desc (skillDesc) {
        this.runtime.desc = skillDesc
        return this
    }

    inputFormat (inputFormat) {
        this.runtime.inputFormat = inputFormat
        return this
    }

    handler (skillHandler) {
        this.runtime.handler = skillHandler
        return this
    }

    register () {
        let missing = []
        if (!this.runtime.name) missing.push('name')
        if (!this.runtime.desc) missing.push('desc')
    }
}

class Skills {
    constructor (Agently) {
        this.debug = Agently.debug
        this.skillList = {}
        this.Manage = new SkillsManage(this)
    }
}

module.exports = Skills