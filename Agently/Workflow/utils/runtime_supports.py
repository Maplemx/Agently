from ..lib.constants import DEFAULT_INPUT_HANDLE_VALUE, DEFAULT_OUTPUT_HANDLE_VALUE
from .find import find_by_attr

def get_default_input_val(inputs_with_handle_name: dict, default_val = None):
  if DEFAULT_INPUT_HANDLE_VALUE in inputs_with_handle_name:
    return inputs_with_handle_name[DEFAULT_INPUT_HANDLE_VALUE] or default_val
  for hanldle in inputs_with_handle_name:
    return inputs_with_handle_name[hanldle] or default_val
  return default_val

def get_default_handle(handles, handle_type = 'inputs'):
  if not handles:
    return None
  default_handle_name = DEFAULT_INPUT_HANDLE_VALUE if handle_type == 'inputs' else DEFAULT_OUTPUT_HANDLE_VALUE
  handle_list = handles[handle_type] or []
  default_handle = find_by_attr(handle_list, 'handle', default_handle_name)
  if default_handle:
    return default_handle
  elif len(handle_list) > 0:
    return handle_list[0]
  return None
