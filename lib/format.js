function toJSONString (origin, layer = 0) {
    const isDict = (obj) => Object.prototype.toString.call(obj) === '[object Object]',
          insertTab = (layer) => {
              let content = ''
              for (let i = 0; i < layer; i++) {
                  content += '\t'
              }
              return content
          }
    if (isDict(origin)) {
        let content = ''
        if (layer > 0) content += '\n'
        content += `${ insertTab(layer) }{\n`
        for (let key in origin) {
            content += `${ insertTab(layer + 1) }"${ key }": ${ toJSONString(origin[key], layer + 1) }\n`
        }
        content += `${ insertTab(layer) }},`
        return content
    } else {
        return typeof(origin) === 'string'
               || typeof(origin) === 'number'
               ? origin
               : JSON.stringify(origin)
    }
}

function extractWarpedContent (origin) {
    const regexp = /<\$\$\$node=(.*?)>([\s\S]*?)<\/\$\$\$>/ig
    let finalResult = {},
        extractResult
    while ((extractResult = regexp.exec(origin)) !== null) {
        finalResult[extractResult[1]] = extractResult[2]
    }
    return finalResult
}

//Thanks to GPT 4
function findJSONString(str) {
    let openBraces = 0;
    let closeBraces = 0;
    let jsonStartIndex;

    for (let i = 0; i < str.length; i++) {
        const char = str[i];

        if (char === '{') {
            if (openBraces === 0) {
                jsonStartIndex = i;
            }
            openBraces++;
        } else if (char === '}') {
            closeBraces++;
        }

        if (openBraces > 0 && openBraces === closeBraces) {
            return str.slice(jsonStartIndex, i+1);
        }
    }

    //throw new Error('Invalid JSON string');
    return '{}'
}

exports.toJSONString = toJSONString
exports.extractWarpedContent = extractWarpedContent
exports.findJSONString = findJSONString