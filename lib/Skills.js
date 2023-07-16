class SkillsManage {
    constructor (Skills) {
        this.setSkill = Skills.setSkill
        this.getSkillList = Skills.getSkillList
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

    activeFormat (activeFormat) {
        this.runtime.activeFormat = activeFormat
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
        if (!this.runtime.handler) missing.push('handler')
        if (missing.length === 0) {
            this.setSkill(this.runtime.name, { ...this.runtime })
            this.runtime = {}
            return { status: 200 }
        } else {
            const msg = `[Skill Register] Failed: missing ${ JSON.stringify(missing) }`
            this.debug(msg)
            this.runtime = {}
            return { status: 400, msg: msg }
        }
    }

    update () {
        if (!this.runtime.name) {
            const msg = `[Skill Update] Failed: Update require skill name`
            this.debug(msg)
            return { status: 400, msg: msg }
        }
        const skill = this.getSkillList()[this.runtime.name]
        if (!skill) {
            const msg = `[Skill Update] Failed: Can not find skill "${ this.runtime.name }"`
            this.debug(msg)
            return { status: 400, msg: msg }
        }
        for (let key in this.runtime) {
            skill[key] = this.runtime[key]
        }
        this.setSkill(this.runtime.name, skill)
        this.runtime = {}
        return { status: 200 }
    }
}

class Skills {
    constructor (Agently) {
        const self = this
        this.debug = Agently.debug
        this.skillList = {}
        this.setSkill = (skillName, skill) => self.skillList[skillName] = skill
        this.getSkillList = () => self.skillList
        this.Manage = new SkillsManage(this)
    }
}

module.exports = Skills