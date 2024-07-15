import functools

def create_connection_symbol(chunk, handle_name):
  """生成 chunk 连接字符"""
  return f"{get_display_name(chunk)}({handle_name})"

def create_symbol(chunk):
  """生成 chunk 符号"""
  return f"{chunk['id']}({get_display_name(chunk)})"

def get_display_name(chunk):
  return fix_display_text(chunk["title"] or f'chunk-{chunk["id"]}' or 'Unknow chunk')

def fix_display_text(label: str):
  """修复文本展示，避免特殊字符"""
  if not label:
      return label
  escaped_string = label.replace('"', '&quot;')
  return f'"{escaped_string}"'


def deep_copy_simply(obj):
  """简单深拷贝，只处理 dict / list"""
  if isinstance(obj, list):
    return [deep_copy_simply(item) for item in obj]
  elif isinstance(obj, dict):
    return {key: deep_copy_simply(value) for key, value in obj.items()}
  else:
    return obj
