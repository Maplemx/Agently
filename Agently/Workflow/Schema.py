from .utils.verify import validate_dict
from .utils.find import has_target_by_attr, find_by_attr
from .Chunk import SchemaChunk
from .lib.constants import DEFAULT_INPUT_HANDLE_VALUE, DEFAULT_OUTPUT_HANDLE_VALUE, DEFAULT_OUTPUT_HANDLE, DEFAULT_INPUT_HANDLE, EXECUTOR_TYPE_NORMAL

class Schema:
    """
    Workflow 的描述
    """

    def __init__(self, schema_data = { 'chunks': [], 'edges': [] }):
        self.chunks = []
        self.edges = []
        # 依次调用添加方法添加
        (
            self
                .append_raw_chunk_list(schema_data.get('chunks', []))
                .connect_with_edges(schema_data.get('edges', []))
        )
    
    def create_chunk(self, type = EXECUTOR_TYPE_NORMAL, executor: callable = None, **chunk_desc) -> SchemaChunk:
        """
        根据 chunk 的描述，创建 chunk 实例
        """
        chunk_inst = SchemaChunk(
            workflow_schema=self,
            type=type,
            executor=executor,
            **chunk_desc
        )
        self.append_raw_chunk(chunk_inst.get_raw_schema())
        return chunk_inst

    def append_raw_chunk(self, chunk: dict):
        """
        添加节点，必须包含 id, type, handles(连接点，{'inputs': [], 'outputs': []}) 字段，如没有 handles 字段，则会自动追加上默认设置
        """
        # 校验必填字段
        verified_res = validate_dict(chunk, ['id', 'type'])
        if verified_res['status'] == False:
            raise ValueError(f"Missing required key: '{verified_res['key']}'")

        chunk_copy = chunk.copy()
        # 如果没有配置 handles，则自动追加上
        if 'handles' not in chunk_copy:
            chunk_copy['handles'] = {
                'inputs': [DEFAULT_INPUT_HANDLE.copy()],
                'outputs': [DEFAULT_OUTPUT_HANDLE.copy()]
            }
        else:
            if 'inputs' not in chunk_copy['handles']:
                chunk_copy['handles']['inputs'] = [DEFAULT_INPUT_HANDLE.copy()]
            if 'outputs' not in chunk_copy['handles']:
                chunk_copy['handles']['outputs'] = [
                    DEFAULT_OUTPUT_HANDLE.copy()]
        
        # 检查是否有重名的 chunk
        if has_target_by_attr(self.chunks, 'id', chunk_copy['id']):
            raise ValueError(
                f"The Chunk with the existing id '{chunk_copy['id']}' already exists.")
        self.chunks.append(chunk)
    
    def append_raw_chunk_list(self, chunks: list):
        for chunk in chunks:
            self.append_raw_chunk(chunk)
        return self

    def del_chunk(self, chunk_id):
        """
        删除节点
        """
        self.chunks = [
            chunk for chunk in self.chunks if chunk.get("id") != chunk_id]
        # 清理相关的边(起点/终点为当前节点的边)
        self.edges = [
            edge for edge in self.edges if edge.get("source") != chunk_id and edge.get("target") != chunk_id]
    
    def get_chunk(self, chunk_id):
        return find_by_attr(self.chunks, 'id', chunk_id)

    def connect_chunk(self, source_chunk_id, target_chunk_id, source_handle=DEFAULT_OUTPUT_HANDLE_VALUE, target_handle=DEFAULT_INPUT_HANDLE_VALUE, condition: callable = None):
        """
        连接两个节点，分别输入：源节点id、目标节点id、源节点输出句柄（可选，默认为源节点的输出点）、目标节点的输入句柄（可选，默认为目标节点的输入点）
        """
        if source_chunk_id == target_chunk_id:
            raise ValueError(
                f"The starting point and the endpoint have the same value: '{target_chunk_id}'")
        source_chunk = None
        target_chunk = None
        for chunk in self.chunks:
            if chunk['id'] == source_chunk_id:
                source_chunk = chunk
            elif chunk['id'] == target_chunk_id:
                target_chunk = chunk

        # 判断节点是否存在
        if source_chunk is None or target_chunk is None:
            raise ValueError('Cannot find corresponding start or end node')

        # 判断句柄是否存在
        source_output_handles = source_chunk.get(
            'handles', {'inputs': [], 'outputs': []}).get('outputs', [])
        if has_target_by_attr(source_output_handles, 'handle', source_handle) == False:
            raise ValueError(
                f'Source node "{source_chunk.get("title", source_chunk_id)}({source_chunk_id})" lacks output endpoint: {source_handle}')

        target_output_handles = target_chunk.get(
            'handles', {'inputs': [], 'outputs': []}).get('inputs', [])
        if has_target_by_attr(target_output_handles, 'handle', target_handle) == False:
            raise ValueError(
                f'Target node "{target_chunk.get("title", target_chunk_id)}({target_chunk_id})" lacks input endpoint: {target_handle}')

        self.edges.append({
            'source': source_chunk_id,
            'target': target_chunk_id,
            'source_handle': source_handle or DEFAULT_OUTPUT_HANDLE_VALUE,
            'target_handle': target_handle or DEFAULT_INPUT_HANDLE_VALUE,
            'condition': condition # 连通的开关条件，默认直连
        })
    
    def get_edge(self, edge_id):
        return find_by_attr(self.edges, 'id', edge_id)
    
    def connect_with_edges(self, edges: list):
        """
        批量添加连接，要求输入为 {"source": str, "target": str, "source_handle"?: str, "target_handle"?: str} 形式构成的数组
        """
        for edge in edges:
            self.connect_chunk(
                edge.get('source'),
                edge.get('target'),
                edge.get('source_handle', DEFAULT_OUTPUT_HANDLE_VALUE),
                edge.get('target_handle', DEFAULT_INPUT_HANDLE_VALUE),
                edge.get('condition') or None
            )
        return self

    def del_connection(self, source_chunk_id, target_chunk_id, source_handle=DEFAULT_OUTPUT_HANDLE_VALUE, target_handle=DEFAULT_INPUT_HANDLE_VALUE):
        """
        取消连线，分别输入：源节点id、目标节点id、源节点输出句柄（可选，默认为源节点的输出点）、目标节点的输入句柄（可选，默认为目标节点的输入点）
        """
        edges = []
        for edge in self.edges:
            if not (
                edge.get("source") == source_chunk_id and
                edge.get("target") == target_chunk_id and
                (source_handle is None or edge.get('source_handle') == source_handle) and
                (target_handle is None or edge.get('target_handle') == target_handle)
            ):
                edges.append(edge)
        # 有变更时赋值
        if len(edges) != len(self.edges):
            self.edges = edges
