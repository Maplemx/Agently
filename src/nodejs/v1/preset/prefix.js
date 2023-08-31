const format = require('../lib/format')

module.exports = (Agently) => {
    Agently.ProcessUnit.Manage
        //Generate system message to set agent's role settings
        //ONLY WORKS WHEN role HAVE AT LEAST 1 PROPERTY
        //input data example:
        //role = { 'Character': 'Love smiling and always be positive', 'Profession': 'Science Teacher' }
        .generateRole(
            (role) => {
                let content = `# Role\n`
                for (let key in role) {
                    content += `**${ key }**: ${ role[key] }\n`
                }
                return { role: 'system', content: content }
            }
        )
        //Generate system message to set agent's status (usually used for game role-play)
        //ONLY WORKS WHEN Agent.useStatus() IS STATED
        //input data example:
        //status = { status: { playerStatus: { HP: 100, SP: 100, MP: 0 } }, getStatus: function() }
        //you can use method like getStatus('playerStatus.HP') to get the value of specific property
        .generateStatus(
            (status) => {
                let content = `# Assistant Status\n`
                content += format.toJSONString(status.status)
                return { role: 'system', content: content }
            }
        )
        //Generate assistant message to tell agent some memories it should remember
        //ONLY WORKS WHEN Agent.useMemory() IS STATED
        //input data example:
        //memories = { 'Experience': 'I lived in countryside in childhood.', 'Friends': 'User and I have a common friend named Sara who lived in LA.' }
        .generateMemories(
            (memories) => {
                let content = `I remember:\n`
                for (let key in memories.memories) {
                    content += `* [${ key }]: ${ format.toJSONString(memories.memories[key]) }\n`
                }
                return { role: 'assistant', content: content }
            }
        )
        //Generate assistant message to tell agent all skills it can use
        //ONLY WORKS WHEN Agent.useSkills() IS STATED
        .generateSkillTips(
            (agentUsedSkillNameList, completeSkillList) => {
                if (agentUsedSkillNameList.length > 0) {
                    let content = `You can use skills list below:\n# SKILL_LIST\n\n`
                    for (let i = 0; i < agentUsedSkillNameList.length; i++) {
                        const skill = completeSkillList[agentUsedSkillNameList[i]]
                        if (skill) {
                            content += `## [${ skill.name }]: \n` +
                            `* desc: ${ skill.desc }\n` +
                            `* ACTIVE_DATA_FORMAT: ${ format.toJSONString(skill.activeFormat) }\n\n`
                        }
                    }
                    return { role: 'system', content: content }
                } else {
                    return []
                }
            }
        )
        .generateSkillJudgePrompt(
            (prompt, skillList) => {
                return {
                    role: 'user',
                    content : `# INPUT\n` +
                        `input = ${ JSON.stringify(prompt.input) }\n\n` +
                        `# OUTPUT PROCESS RULE\n` +
                        `Judge if to reply #INPUT, which skills you want to use?\n` +
                        `OUTPUT JSON ONLY that can be parsed by python.\n` +
                        `If you don't want to use skills, output []\n\n` +
                        `# OUTPUT FORMAT\n\n` +
                        `TYPE: JSON\n\n` +
                        `FORMAT DEFINITION:\n\n` +
                        `\`\`\`JSON\n` +
                        format.toJSONString([
                            {
                                skillName: '<String>,//MUST USE skill name in #SKILL_LIST',
                                data: '<any>,//MUST IN ##{callSkillName}.{ACTIVE_DATA_FORMAT} IF IT IS NOT null!'
                            },
                        ]) +
                        `\n\`\`\`\n\n` +
                        `# OUTPUT\n` +
                        `output = `
                }
            }
        )
        //Generate context messages (usually saved in multi-round chat or appendContext()/coverContext() by user)
        //ONLY WORKS WHEN AgentSession.setLoadContext(true) IS SET
        //input data example:
        //context = { full: [Messages of full context], request: [Messages used to request last time] }
        .generateContext(
            (context) => context.request
        )
        //Method to shorten context messages if it is to long (exceed maxContentLength)
        //By default, this method will cut messages from the earliest ones to the most recent ones.
        //You can change this method to summarize or whatever you want
        .shortenContext(
            (requestContext, fullContext, maxContentLength) => {
                let newContext = Array.from(requestContext)
                for (let i = 0; i < newContext.length; i++) {
                    if (JSON.stringify(newContext).length <= maxContentLength) break
                    newContext.splice(i, 1)
                    i--
                }
                return newContext
            }
        )
        //Generate user message for current request prompt
        //If user only state AgentSession.input() then .start(), it will simply generate { role: 'user', content: prompt.input }
        //Or it will generate prompt with structure
        //input data example:
        //prompt = {
        //    input: <String | Object>,
        //    prompt: <Array of { title: <String>, content: <String> }>,/*Each item is a paragraph of prompt with title and content>*/
        //    output: { desc: <String | Object>, type: <String, optional> },/*If desc is Object and type is undefined, type will be set to 'JSON' by default. Only works when multiOutput is not stated.*/
        //    multiOutput: <Array of { title: <String>, desc: <String | Object>, type: <String> }>,/*Each item is a segment of output*/
        //}
        .generatePrompt(
            (prompt) => {
                if (prompt.input && prompt.prompt.length === 0 && !prompt.output && prompt.multiOutput.length === 0) {
                    return { role: 'user', content: prompt.input }
                } else {
                    let content = '# INPUT\n'
                    content += `input = ${ JSON.stringify(prompt.input) }\n\n`
                    for (let i = 0; i < prompt.prompt.length; i++) {
                        content += `# ${ prompt.prompt[i].title }\n${ format.toJSONString(prompt.prompt[i].content) }\n`
                    }
                    content += '\n'
                    if (prompt.multiOutput.length > 0) {
                        content += `# OUTPUT FORMAT\n\n` +
                                   `## RULE\nEach output block must be warp by tag "<$$$node={nodeValue}>...</$$$>"!\n\n` +
                                   `## FULL OUTPUT CONTENT\n`
                        for (let i = 0; i < prompt.multiOutput.length; i++) {
                            content += `<$$$node=${ prompt.multiOutput[i].title }>\n`
                            if (!prompt.multiOutput[i].type) {
                                if (Object.prototype.toString.call(prompt.multiOutput[i].desc) === '[object Object]') {
                                    prompt.multiOutput[i].type = 'JSON'
                                } else {
                                    prompt.multiOutput[i].type = 'customize'
                                }
                            }
                            if (prompt.multiOutput[i].type === 'JSON') {
                                content += `TYPE: ${ prompt.multiOutput[i].type } can be parsed in Python\n\nFORMAT DEFINITION:\n\n\`\`\`${ prompt.multiOutput[i].type }\n${ format.toJSONString(prompt.multiOutput[i].desc) }\n\`\`\`\n\n`
                            } else {
                                content += `\`\`\`${ prompt.multiOutput[i].type }\n${ prompt.multiOutput[i].desc }\n\`\`\`\n\n`
                            }
                            content += `</$$$>\n\n`
                        }
                    } else if (prompt.output) {
                        content += '# OUTPUT FORMAT\n\n'
                        if (!prompt.output.type) {
                            if (Object.prototype.toString.call(prompt.output.desc) === '[object Object]') {
                                prompt.output.type = 'JSON'
                            } else {
                                prompt.output.type = 'customize'
                            }
                        }
                        if (prompt.output.type === 'JSON') {
                            content += `TYPE: ${ prompt.output.type } can be parsed in Python\n\nFORMAT DEFINITION:\n\n\`\`\`${ prompt.output.type }\n${ format.toJSONString(prompt.output.desc) }\n\`\`\`\n\n`
                        } else {
                            content += `\`\`\`${ prompt.output.type }\n${ prompt.output.desc }\n\`\`\`\n\n`
                        }
                    }
                    content += `# OUTPUT\n\noutput = `
                    return { role: 'user', content: content }
                }
            }
        )
        .register()
}