const DDG = require('duck-duck-scrape'),
      htmlToText = require('html-to-text'),
      read = require('node-readability'),
      sbd = require('sbd')

function cleanHTML (htmlContent) {
    return htmlToText.convert(htmlContent).replace(/(\[data\:image.+\]|\[http.+\])/ig, '')
}

class Tools {
    constructor (SmartAgent) {
        this.Options = SmartAgent.Options
    }

    async search (query, options) {
        const now = new Date(),
              lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1),
              proxy = this.Options.get('proxy')
        options = options || {}
        options.locale = options.locale || 'zh-cn'
        options.marketRegion = options.marketRegion || 'CN'
        options.offset = options.offset || 2
        options.safeSearch = options.safeSearch || -1
        options.time = options.time || `${ lastMonth.toISOString().slice(0, 10) }..${ now.toISOString().slice(0, 10) }`

        const result = await DDG.search (
            query,
            options,
            proxy && proxy.host && proxy.port
            ? { proxy: `http://${ proxy.host }:${ proxy.port }` }
            : undefined
        )

        return result.results.map(
            (item) => {
                return {
                    title: cleanHTML(item.title),
                    description: cleanHTML(item.description),
                    url: item.url,
                }
            }
        )
    }

    async news (query, options) {
        const proxy = this.Options.get('proxy')        
        options = options || {}
        options.locale = options.locale || 'zh-cn'
        options.offset = options.offset || 2
        options.safeSearch = options.safeSearch || -1
        options.time = options.time || 'w'

        const result = await DDG.searchNews (
            query,
            options,
            proxy && proxy.host && proxy.port
            ? { proxy: `http://${ proxy.host }:${ proxy.port }` }
            : undefined
        )

        return result.results.map(
            (item) => {
                return {
                    title: cleanHTML(item.title),
                    excerpt: cleanHTML(item.excerpt),
                    newsDate: new Date(item.date * 1000).toLocaleString(),
                    url: item.url,
                    fromNow: item.relativeTime,
                }
            }
        )
    }

    async browse (url, options) {
        //const proxy = this.Options.get('proxy')
        options = options || {}
        options.encoding = options.encoding || 'utf-8'
        /*options.proxy =
            proxy && proxy.host && proxy.port
            ? { proxy: `http://${ proxy.host }:${ proxy.port }` }
            : undefined*/
        const result = new Promise(
            (solve) => {
                read(
                    url,
                    options,
                    (err, article, meta) => {
                        let result = {}
                        if (err) {
                            result = { title: 'Error', content: JSON.stringify(err) }
                        } else {
                            result = { title: cleanHTML(article.title), content: cleanHTML(article.content) }
                            article.close()
                        }                        
                        solve(result)
                    }
                )
            }
        )
        return await result
    }

    cut (text, expectedLength = 2000) {
        const paragraphs = text.replace(/\n+/ig, `\n`).split(`\n`)
        let chunks = [''],
            chunkNum = 0
        for (let i = 0; i < paragraphs.length; i++) {
            let newChunks = [''],
                newChunkNum = 0
            const sentences = sbd.sentences(paragraphs[i], { "newline_boundaries": true, "html_boundaries": false, "sanitize": false })
            for (let j = 0; j < sentences.length; j++) {
                if (newChunks.length < expectedLength) {
                    newChunks[newChunkNum] += sentences[j] || ''
                } else {
                    newChunkNum++
                    newChunks[newChunkNum] = sentences[j] || ''
                }
            }
            if (newChunks.length === 1) {
                if ((chunks[chunkNum] + newChunks[0]).length < expectedLength ) {
                    chunks[chunkNum] += newChunks[0] + '\n'
                } else {
                    chunkNum++
                    chunks[chunkNum] = newChunks[0] + '\n'
                }
            } else {
                for (let j = 0; j < newChunks.length; j++) {
                    if ((chunks[chunkNum] + newChunks[j]).length < expectedLength ) {
                        chunks[chunkNum] += newChunks[j] + '\n'
                    } else {
                        chunkNum++
                        chunks[chunkNum] = newChunks[j] + '\n'
                    }
                }
            }
        }
        return chunks
    }
}

module.exports = Tools