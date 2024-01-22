from .MainExecutor import MainExecutor
from .utils.exec_tree import generate_exec_tree
from .Schema import Schema
from .executors.install import mount_built_in_executors

class Workflow:
  def __init__(self, schema_data: dict, handler, settings = {}):
    """
    Workflow，初始参数 schema_data 形如 { 'chunks': [], 'edges': [] }，handler 为要处理响应的函数
    """
    self.handler = handler
    self.settings = settings
    self.schema = Schema(schema_data or {'chunks': [], 'edges': []})
    self.executor = MainExecutor(handler, settings)
    mount_built_in_executors(self.executor)
  
  def startup(self):
    exec_logic_tree = generate_exec_tree(self.schema)
    self.executor.startup(exec_logic_tree)
  
  def reset(self, schema_data: dict):
    self.schema = Schema(schema_data or {'chunks': [], 'edges': []})