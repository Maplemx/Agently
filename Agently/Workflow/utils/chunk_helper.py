
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
