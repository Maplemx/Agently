from ...lib.Store import Store
from ...lib.constants import WORKFLOW_END_DATA_HANDLE_NAME

def end_executor(inputs, store: Store, **sys_info):
    sys_info['sys_store'].set(WORKFLOW_END_DATA_HANDLE_NAME, inputs)
    return inputs