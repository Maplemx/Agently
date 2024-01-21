from ..lib.ChunkExecutorABC import ChunkExecutorABC
from ..utils.find import find_by_attr
from ..lib.constants import EXECUTOR_TYPE_NORMAL
import Agently
import re

class AgentRequestExecutor(ChunkExecutorABC):
  def __init__(self, chunk_desc: dict, main_executor):
    self.type = EXECUTOR_TYPE_NORMAL
    self.chunk = chunk_desc
    self.main_executor = main_executor

  def exec(self, inputs_with_handle_name: dict):
    global_input_history = self.main_executor.memory.get('global_user_inputs') or []
    global_settings = self.main_executor.settings
    chunk_settings = self.chunk['data'].get('settings') or {}
    agent_factory = global_settings.get(
      'agent_factory',
      Agently.AgentFactory(is_debug=global_settings.get('debug', False))
    )
    agent = agent_factory.create_agent()
    role_params = {
        "global_user_inputs_history": '\n'.join(global_input_history)
    } if chunk_settings.get('enable_history', True) else {}
    # 取所有依赖数据
    full_inputs = inputs_with_handle_name
    chunk_data = self.chunk.get('data', {})

    # 模板字符串解析方法
    def resolve_template(template_str: str, template_data: dict):
      def replace(match):
        key = match.group(1)
        # 处理全局常量
        if key == '$$全局输入':
          return global_input_history[-1] if len(global_input_history) > 0 else 'None'
        # 找到当前handle_title 对应的 handle_name
        handle_name = find_by_attr(chunk_data.get('handles').get('inputs', []), 'handle_title', key)
        # 再根据 handle_name 拿到对应的数据
        return template_data.get(handle_name, match.group())
      pattern = re.compile(r'@([^\s]+)')
      result = pattern.sub(replace, template_str)
      return result

    agent_input = ''
    settings = chunk_settings.get('commands', [])
    for agent_settings in settings:
      # Output 的设置
      if agent_settings['name'] == 'Output':
        output_params = {}
        for output in agent_settings['value']['outputs']:
          if output['type'] == 'string':
            output_params[output['key']] = ('String', output['description'])
          elif output['type'] == 'list':  # description 格式为 "String:解释"
            split_desc = output['description'].split(':')
            # 尝试提取申明的类型，如果没有，则使用 String 作为默认类型
            list_type = split_desc[0] if len(split_desc) >= 2 else 'String'
            # 剩余部分为对字段的描述
            list_desc = ':'.join(split_desc[1:] if len(
                split_desc) >= 2 else split_desc)
            output_params[output['key']] = [(list_type, resolve_template(list_desc, full_inputs))]
          elif output['type'] == 'number':
            output_params[output['key']] = (
                'Number', resolve_template(output['description'], full_inputs))
          elif output['type'] == 'boolean':
            output_params[output['key']] = (
                'Boolean', resolve_template(output['description'], full_inputs))
          else:
            output_params[output['key']] = (
                'String', resolve_template(output['description'], full_inputs))
        # 尝试设值
        agent.output(output_params)

      # Role 的设置
      elif agent_settings['name'] == 'Role':
        for role_key in agent_settings['value']:
          role_params[role_key] = resolve_template(
              agent_settings['value'][role_key]['description'], full_inputs)

      # Instruct 的设置
      elif agent_settings['name'] == 'Instruct':
        if agent_settings['value']['content']:
          agent.instruct(resolve_template(
              agent_settings['value']['content'], full_inputs))

      # Input 仅取值，在最后调用
      elif agent_settings['name'] == 'Input':
        if agent_settings['value']['content']:
          agent_input = resolve_template(
              agent_settings['value']['content'], full_inputs)

    # 设置 Role(包含初始设置和默认设置)
    agent.set_role(role_params)

    # 修正 Input
    if agent_input == '' or not agent_input:
      agent_input = full_inputs.get('input', 'Complete the task as required')

    # 最终的执行
    res = (
        agent
        .input(agent_input)
        .start()
    )
    return {
        "status": "success",
        "dataset": res
    }
    
