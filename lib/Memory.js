class Memory {
    constructor (SmartAgent) {
        this.Options = SmartAgent.Options
        this.fullMemory = []
        this.runtimeMemory = []
        this.instructDict = {}
        this.memoDict = {}
        this.overflowHandler = this.cut
    }

    cut (memory, length) {
        let newMemory = Array.from(memory)
        for (let i = 0; i < newMemory.length; i++) {
            if (JSON.stringify(newMemory).length <= length) break
            newMemory.splice(i, 1)
            i--
        }
        return newMemory
    }

    setOverflowHandler (overflowHandler) {
        this.overflowHandler = overflowHandler
        return this
    }

    addMemory (memoryFragment) {
        this.fullMemory = this.fullMemory.concat(memoryFragment)
        this.runtimeMemory = this.runtimeMemory.concat(memoryFragment)
        return this
    }

    loadInstruct (instructFragment) {
        for (let key in instructFragment) {
            this.instructDict[key] =
                typeof(instructFragment[key] === 'string')
                || typeof(instructFragment[key] === 'number')
                ? instructFragment[key]
                : JSON.stringify(instructFragment[key])
        }
        return this
    }

    setInstruct (key, value) {
        if (value) {
            this.instructDict[key] =
                typeof(value === 'string')
                || typeof(value === 'number')
                ? value
                : JSON.stringify(value)
        } else {
            delete this.instructDict[key]
        }
        return this
    }

    getInstruct () {
        return this.instructDict
    }

    loadMemo (memoFragment) {
        for (let key in memoFragment) {
            this.memoDict[key] =
                typeof(memoFragment[key] === 'string')
                || typeof(memoFragment[key] === 'number')
                ? memoFragment[key]
                : JSON.stringify(memoFragment[key])
        }
        return this
    }

    setMemo (key, value) {
        this.memoDict[key] = 
            typeof(value === 'string')
            || typeof(value === 'number')
            ? value
            : JSON.stringify(value)
        return this
    }

    getMemo (key) {
        return this.memoDict[key]
    }

    async getMemory (needBreakLimitation = false) {
        if (JSON.stringify(this.runtimeMemory).length > this.Options.get('memoryLength') && !needBreakLimitation) {
            if (this.Options.get('debug')) console.log(`[Memory Overflow]\nCurrent Memory: ${ JSON.stringify(this.runtimeMemory) }`)
            this.runtimeMemory = this.overflowHandler(this.runtimeMemory, this.Options.get('memoryLength'))
            if (this.Options.get('debug')) console.log(`Shorten Memory: ${ JSON.stringify(this.runtimeMemory) }`)
        }
        return this.runtimeMemory
    }
}

module.exports = Memory