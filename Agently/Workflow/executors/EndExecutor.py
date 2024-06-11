from ..lib.Store import Store
from ..lib.constants import WORKFLOW_END_DATA_HANDLE_NAME

def end_executor(inputs, store: Store):
    store.set(WORKFLOW_END_DATA_HANDLE_NAME, inputs.get('default'))
    return inputs