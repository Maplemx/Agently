from .MainExecutor import MainExecutor
from .utils.exec_tree import resolve_runtime_data
from .Schema import Schema
from ..utils import RuntimeCtx
from .._global import global_settings
from .executors.install import mount_built_in_executors
from .lib.constants import EXECUTOR_TYPE_NORMAL, DEFAULT_INPUT_HANDLE_VALUE, DEFAULT_OUTPUT_HANDLE_VALUE

class Workflow:
    def __init__(self, *, schema_data: dict = None, settings: dict = {}):
        """
        Workflow，初始参数 schema_data 形如 { 'chunks': [], 'edges': [] }，handler 为要处理响应的函数
        """
        # 处理设置
        self.settings = RuntimeCtx(parent = global_settings)
        if settings:
            self.settings.update_by_dict(settings)
        # 初始 schema
        self.schema = Schema(schema_data or {'chunks': [], 'edges': []})
        # 初始化执行器
        self.executor = MainExecutor(settings)
        # 装载内置类型
        mount_built_in_executors(self.executor)
        # Chunk Storage
        self.chunks = {}

    def chunk(self, chunk_id: str, type=EXECUTOR_TYPE_NORMAL, **chunk_desc):
        def create_chunk_decorator(func: callable):
            return self.chunks.update({
                chunk_id: self.schema.create_chunk(
                        executor = func,
                        type = type,
                        **chunk_desc
                    )
            })
        return create_chunk_decorator
    
    def start(self):
        runtime_data = resolve_runtime_data(self.schema)
        self.executor.start(runtime_data)
    
    def reset(self, schema_data: dict):
        self.schema = Schema(schema_data or {'chunks': [], 'edges': []})
    
    def draw(self, type='mermaid'):
        """绘制出图形，默认使用 mermaid，可点击 https://mermaid-js.github.io/mermaid-live-editor/edit 粘贴查看效果"""
        edges = self.schema.edges
        chunks = self.schema.chunks
        chunk_map = {}
        for chunk in chunks:
            chunk_map[chunk['id']] = chunk
        
        def to_node(chunk):
            chunk_name = chunk["title"] or f'chunk-{chunk["id"]}' or 'Unknow chunk'
            return f"{chunk['id']}({chunk_name})"

        graph_partial_list = []
        label_split = ' -->-- '
        condition_label_split = ' -- ? -- '
        for idx, edge in enumerate(edges):
            source = chunk_map[edge['source']] if edge.get('source') else None
            target = chunk_map[edge['target']] if edge.get('target') else None
            if source and target:
                """连接起点和终点"""
                # 处理条件判断
                condition_symbol = None
                if edge.get('condition'):
                    condition_symbol = f"condition{idx}" + "{?}"

                # 处理连接手柄
                start_label_symbol = ''
                end_label_symbol = ''
                if edge.get('source_handle') and edge.get('target_handle'):
                    start_label_symbol = edge.get('source_handle')
                    end_label_symbol = edge.get('target_handle')
                    
                full_labels_symbol = f"|{start_label_symbol}{condition_label_split if condition_symbol else label_split}{end_label_symbol}|"
                graph_partial_list.append(f"{to_node(source)} -.-> {full_labels_symbol} {to_node(target)}")
        
        return "flowchart LR\n" + '\n'.join(map(lambda part: '    ' + part, graph_partial_list))
