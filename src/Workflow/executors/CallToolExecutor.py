from ..lib.ChunkExecutorABC import ChunkExecutorABC
from ..utils.verify import validate_dict
from ..utils.runtime_supports import get_default_input_val
from ..lib.constants import EXECUTOR_TYPE_NORMAL
import Agently

class CallToolExecutor(ChunkExecutorABC):
    def __init__(self, chunk_desc: dict, main_executor):
        self.type = EXECUTOR_TYPE_NORMAL
        self.chunk = chunk_desc
        self.main_executor = main_executor
        self.global_input_history = []

    def exec(self, inputs_with_handle_name: dict):
        main_settings = self.main_executor.settings
        chunk_settings = self.chunk['data'].get('settings', {})
        # 校验必填字段
        verified_res = validate_dict(chunk_settings, ['tool', 'tool_executor'])
        if not tool_name or not tool_executor:
            raise ValueError(f"Missing required key: '{verified_res['key']}'")
        # 取出要执行的工具及工具处理方法
        tool_name = chunk_settings.get('tool')
        tool_executor = chunk_settings.get('tool_executor')
        agent_factory = main_settings.get(
          'agent_factory',
          Agently.AgentFactory(is_debug=main_settings.get('debug', False))
        )
        agent = agent_factory.create_agent()

        # 判断是否执行
        judge_res = (
            agent
            .must_call(tool_name)
            .input(get_default_input_val(inputs_with_handle_name, 'Execute the current task'))
            .start()
        )
        executed_res = None
        if judge_res['can_call']:
            executed_res = tool_executor(**judge_res["args"])
                
        return {
            "status": "success",
            "dataset": {
                **judge_res,
                "result": executed_res
            }
        }
    
