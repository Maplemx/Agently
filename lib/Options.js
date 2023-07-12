class Options {
    constructor (options) {
        options = options || {}
        this.options = {
            debug: options.debug || false,
            retryTimes: options.retryTimes || 3,
            retryPause: options.retryPause || 1000,
        }
    }

    set (key, value) {
        if (!key) return false
        const splitedKey = key.split('.')
        let current = this.options
        for (let i = 0; i < splitedKey.length - 1; i++) {
            if (splitedKey[i] && splitedKey[i] !== '' && !current[splitedKey[i]]) {
                current[splitedKey[i]] = {}
            }
            current = current[splitedKey[i]]
        }
        current[splitedKey[splitedKey.length - 1]] = value
        return this
    }

    get (key) {
        key = key || ''
        const splitedKey = key.split('.')
        let result = this.options
        for (let i = 0; i < splitedKey.length; i++) {
            if (splitedKey[i] && splitedKey[i] !== '') result = result[splitedKey[i]]
            if (!result) return undefined
        }
        return result
    }
}

module.exports = Options