class Options {
    constructor (options) {
        this.options = {
            debug: options.debug || false,
            retryTimes: options.retryTimes || 3,
            retryWait: options.retryWait || 2000,
            memoryLength: options.memoryLength || 3000,
            auth: options.auth || {},
            proxy: options.proxy || {},
            language: options.language,
            knowTime: options.knowTime || false,
        }
    }

    set (key, value) {
        this.options[key] = value
        return this
    }

    get (key) {
        return this.options[key]
    }
}

module.exports = Options