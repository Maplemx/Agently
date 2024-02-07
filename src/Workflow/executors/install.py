from .StartExecutor import start_executor
from ..MainExecutor import MainExecutor

def mount_built_in_executors(main_executor: MainExecutor):
    """
    挂载内置的执行器
    """
    main_executor.regist_executor('Start', start_executor)