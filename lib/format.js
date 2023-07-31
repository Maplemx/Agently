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
        if (layer > 0) {
            content += `${ insertTab(layer) }},`
        } else {
            content += `}`
        }
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

/*function findJSONString(str) {
    let openBraces = 0;
    let closeBraces = 0;
    let openSquareBrackets = 0;
    let closeSquareBrackets = 0;
    let jsonStartIndex;
    let insideQuotes = false;

    for (let i = 0; i < str.length; i++) {
        const char = str[i];

        if (char === '"') {
            insideQuotes = !insideQuotes;
        }

        if (!insideQuotes) {
            if (char === '{') {
                if (openBraces === 0) {
                    jsonStartIndex = i;
                }
                openBraces++;
            } else if (char === '}') {
                closeBraces++;
            } else if (char === '[') {
                if (openSquareBrackets === 0 && openBraces === 0) {
                    jsonStartIndex = i;
                }
                openSquareBrackets++;
            } else if (char === ']') {
                closeSquareBrackets++;
            }

            if ( (openBraces > 0 || openSquareBrackets > 0) && (openBraces === closeBraces) && (openSquareBrackets === closeSquareBrackets)) {
                return str.slice(jsonStartIndex, i+1);
            }
        }
    }

    //throw new Error('Invalid JSON string');
    return JSON.stringify({ emptyChunk: true })
}*/
function findJSONString(str) {
    for (let end = str.length; end > 0; end--) {
        for (let start = 0; start + end <= str.length; start++) {
            try {
                const substring = str.substring(start, start + end);
                if ((substring.startsWith("{") && substring.endsWith("}")) || (substring.startsWith("[") && substring.endsWith("]"))) {
                    const potentialJson = JSON.parse(substring);
                    return JSON.stringify(potentialJson);
                }
            } catch (err) {
                // Ignore errors as they simply mean the current substring is not valid JSON
            }
        }
    }

    //throw new Error("No valid JSON found in input string");
    return JSON.stringify({ emptyChunk: true })
}

exports.toJSONString = toJSONString
exports.extractWarpedContent = extractWarpedContent
exports.findJSONString = findJSONString