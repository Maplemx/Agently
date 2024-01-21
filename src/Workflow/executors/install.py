from .AgentRequestExecutor import AgentRequestExecutor
from .JudgeExecutor import JudgeExecutor
from .CallToolExecutor import CallToolExecutor
from .SaveMemoryExecutor import SaveMemoryExecutor
from .GetMemoryExecutor import GetMemoryExecutor
from .PrintExecutor import PrintExecutor
from .StartExecutor import StartExecutor
from .UserInputExecutor import UserInputExecutor
from ..MainExecutor import MainExecutor

def mount_built_in_executors(main_executor: MainExecutor):
    """
    挂载内置的执行器
    """
    main_executor.regist_executor('AgentRequest', AgentRequestExecutor)
    main_executor.regist_executor('Judge', JudgeExecutor)
    main_executor.regist_executor('CallTool', CallToolExecutor)
    main_executor.regist_executor('SaveMemory', SaveMemoryExecutor)
    main_executor.regist_executor('GetMemory', GetMemoryExecutor)
    main_executor.regist_executor('Print', PrintExecutor)
    main_executor.regist_executor('Start', StartExecutor)
    main_executor.regist_executor('UserInput', UserInputExecutor)