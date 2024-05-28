from ..lib.Store import Store
from ..lib.constants import WORKFLOW_START_DATA_HANDLE_NAME

def end_executor(inputs, store: Store):
    return store.get(WORKFLOW_START_DATA_HANDLE_NAME)