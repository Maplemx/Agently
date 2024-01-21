from ..lib.ChunkExecutorABC import ChunkExecutorABC
from ..lib.constants import EXECUTOR_TYPE_NORMAL
from ..utils.runtime_supports import get_default_input_val, get_default_handle

class UserInputExecutor(ChunkExecutorABC):
    """
    接收用户输入，会从输入处取问题，支持传入多个问题（list）、单个问题(str)
    """
    def __init__(self, chunk_desc: dict, main_executor):
        self.type = EXECUTOR_TYPE_NORMAL
        self.chunk = chunk_desc
        self.main_executor = main_executor

    def exec(self, inputs_with_handle_name: dict):
        # 返回结果的句柄（仅支持单个输出节点，会将所有结果组织成字符串给到该节点）
        output_handle = get_default_handle(self.chunk.get('data').get('handles'), 'outputs')
        if not output_handle:
            return {
                "status": "success",
                "dataset": {}
            }

        chunk_settings = self.chunk.get('data').get('settings') or {}
        persist_question = chunk_settings.get('question')
        questions = []
        # 如果有预设提问，则直接使用该提问
        if persist_question:
            questions = [persist_question]
        # 否则尝试从上游数据中获取提问
        else:
            input_question = get_default_input_val(inputs_with_handle_name)
            if type(input_question) is str:
                questions = [input_question]
            elif type(input_question) is list:
                questions = input_question

        if len(questions) == 0:
            dataset = {}
            return {
                "status": "success",
                "dataset": {
                    output_handle['handle']: ''
                }
            }

        usr_inputs_text_list = []
        for question in questions:
            question_tips = question or 'Please input:'
            answer = input(question_tips)
            usr_inputs_text_list.append(f'{question_tips}: {answer}')

        composed_answer = '\n'.join(usr_inputs_text_list)
        # 当设置为主节点时，会存入记录（可在配置时显式将 major 置为 False 关闭）
        if chunk_settings.get('major'):
            self.main_executor.memory.get(
                'global_user_inputs').append(composed_answer)

        return {
            "status": "success",
            "dataset": {
                output_handle['handle']: composed_answer
            }
        }
