import copy
import logging
from .utils.verify import validate_dict
from .utils.find import has_target_by_attr, find_by_attr, find
from .utils.chunk_helper import create_connection_symbol
from .Chunk import SchemaChunk
from .lib.constants import DEFAULT_INPUT_HANDLE_VALUE, DEFAULT_OUTPUT_HANDLE_VALUE, DEFAULT_OUTPUT_HANDLE, DEFAULT_INPUT_HANDLE, EXECUTOR_TYPE_NORMAL

class Schema:
    """Workflow 的描述"""

    def __init__(self, schema_data = { 'chunks': [], 'edges': [] }, workflow = None, logger: logging.Logger = None):
        self.logger = logger
        self._chunks = []
        self._edges = []
        # 依次调用添加方法添加
        (
            self
                .append_raw_chunk_list(schema_data.get('chunks', []))
                .connect_with_edges(schema_data.get('edges', []))
        )
        self.workflow = workflow
    
    def compile(self):
        """编译处理，得到可用数据"""
        compiled_chunks = copy.deepcopy(self._chunks)
        compiled_edges = copy.deepcopy(self._edges)
        # 处理 1：收集 handle 使用，自动完成 handle 注册
        # 构建 chunk map
        chunk_map = {}
        for chunk in compiled_chunks:
            chunk_map[chunk['id']] = chunk
        # 从连接关系中搜集使用到的 Handle，尝试自动帮助注册
        for edge in compiled_edges:
            source_chunk = chunk_map.get(edge['source'])
            target_chunk = chunk_map.get(edge['target'])
            # 合法校验
            if not source_chunk:
                raise ValueError(
                    f"Compilation failed due to an undefined chunk: '{edge['source']}'")
            elif not target_chunk:
                raise ValueError(
                    f"Compilation failed due to an undefined chunk: '{edge['target']}'")
            # 自动注册使用到的 handle
            if not has_target_by_attr(source_chunk['handles']['outputs'], 'handle', edge['source_handle']):
                source_chunk['handles']['outputs'].append({
                    'handle': edge['source_handle']
                })
            if not has_target_by_attr(target_chunk['handles']['inputs'], 'handle', edge['target_handle']):
                target_chunk['handles']['inputs'].append({
                    'handle': edge['target_handle']
                })
        
        # 针对完全为空的 handle 的 chunk，自动追加默认连接
        for chunk in compiled_chunks:
            if len(chunk['handles']['inputs']) == 0:
                chunk['handles']['inputs'].append(DEFAULT_INPUT_HANDLE.copy())
            if len(chunk['handles']['outputs']) == 0:
                chunk['handles']['outputs'].append(DEFAULT_OUTPUT_HANDLE.copy())

        return {
            'chunks': compiled_chunks,
            'edges': compiled_edges
        }
    
    def create_chunk(self, type = EXECUTOR_TYPE_NORMAL, executor: callable = None, **chunk_desc) -> SchemaChunk:
        """根据 chunk 的描述，创建 chunk 实例"""
        chunk_inst = SchemaChunk(
            workflow_schema=self,
            type=type,
            executor=executor,
            **chunk_desc
        )
        self.append_raw_chunk(chunk_inst.get_raw_schema(use_origin=True))
        return chunk_inst

    def append_raw_chunk(self, chunk: dict):
        """
        添加节点，必须包含 id, type字段，如没有 handles 字段，则会自动追加上默认设置
        """
        # 校验必填字段
        verified_res = validate_dict(chunk, ['id', 'type'])
        if verified_res['status'] == False:
            raise ValueError(f"Missing required key: '{verified_res['key']}'")

        chunk_copy = chunk.copy()
        # 如果没有配置 handles，则自动追加上结构
        if 'handles' not in chunk_copy:
            chunk_copy['handles'] = {
                'inputs': [],
                'outputs': []
            }
        else:
            if 'inputs' not in chunk_copy['handles']:
                chunk_copy['handles']['inputs'] = []
            if 'outputs' not in chunk_copy['handles']:
                chunk_copy['handles']['outputs'] = []
        
        # 检查是否有重名的 chunk
        if has_target_by_attr(self._chunks, 'id', chunk_copy['id']):
            raise ValueError(
                f"The Chunk with the existing id '{chunk_copy['id']}' already exists.")
        self._chunks.append(chunk)
        return self
    
    def append_raw_chunk_list(self, chunks: list):
        """注入多个原生chunk"""
        for chunk in chunks:
            self.append_raw_chunk(chunk)
        return self

    def del_chunk(self, chunk_id):
        """删除节点"""
        self._chunks = [
            chunk for chunk in self._chunks if chunk.get("id") != chunk_id]
        # 清理相关的边(起点/终点为当前节点的边)
        self._edges = [
            edge for edge in self._edges if edge.get("source") != chunk_id and edge.get("target") != chunk_id]
        return self
    
    def get_chunk(self, chunk_id):
        return find_by_attr(self._chunks, 'id', chunk_id)
    
    def get_chunk_by(self, filter: callable):
        return find(self._chunks, filter)

    def connect_chunk(self, source_chunk_id, target_chunk_id, source_handle=DEFAULT_OUTPUT_HANDLE_VALUE, target_handle=DEFAULT_INPUT_HANDLE_VALUE, condition: callable = None, condition_detail: dict = None):
        """
        连接两个节点，分别输入：源节点id、目标节点id、源节点输出句柄（可选，默认为源节点的输出点）、目标节点的输入句柄（可选，默认为目标节点的输入点）
        """
        """
        if source_chunk_id == target_chunk_id:
            raise ValueError(
                f"The starting point and the endpoint have the same value: '{target_chunk_id}'")
        """
        source_chunk = None
        target_chunk = None
        for chunk in self._chunks:
            if chunk['id'] == source_chunk_id:
                source_chunk = chunk
            if chunk['id'] == target_chunk_id:
                target_chunk = chunk

        # 判断节点是否存在
        if source_chunk is None or target_chunk is None:
            raise ValueError('Cannot find target start or end node')

        # 判断句柄是否存在，如果不存在，自动帮其注册
        source_output_handles: list = source_chunk['handles']['outputs']
        if has_target_by_attr(source_output_handles, 'handle', source_handle) == False:
            source_output_handles.append({ 'handle': source_handle })

        target_input_handles: list = target_chunk['handles']['inputs']
        if has_target_by_attr(target_input_handles, 'handle', target_handle) == False:
            target_input_handles.append({'handle': target_handle})
        
        new_edge = {
            'source': source_chunk_id,
            'target': target_chunk_id,
            'source_handle': source_handle or DEFAULT_OUTPUT_HANDLE_VALUE,
            'target_handle': target_handle or DEFAULT_INPUT_HANDLE_VALUE,
            'condition': condition,  # 连通的开关条件，默认直连
            'condition_detail': condition_detail  # 连通的开关条件的类型
        }
        verified_res = self.verify_connection(new_edge)
        if verified_res['status'] == 'error':
            raise ValueError(verified_res['message'])
        elif verified_res['status'] == 'warning':
            self.logger.warn(verified_res["message"])

        self._edges.append(new_edge)
        return self
    
    def verify_connection(self, new_edge: dict):
        """检测连接线的合法性"""
        status_res = { "status": "success", "message": "" }
        is_condition_connection = new_edge.get('condition') is not None
        for edge in self._edges:
            flag = True
            for attr in ['source', 'target', 'source_handle', 'target_handle']:
                if edge.get(attr) != new_edge.get(attr):
                    flag = False
                    break
            # 有相似项，判断是走告警还是走中断，如果是告警，则继续找，看是否有更严重的处理
            if flag:
                source_chunk = self.get_chunk(edge['source'])
                target_chunk = self.get_chunk(edge['target'])
                source_view_name = create_connection_symbol(
                    source_chunk, edge['source_handle'])
                target_view_name = create_connection_symbol(
                    target_chunk, edge['target_handle'])
                # 如果是非条件的情况，直接出报错，然后跳出查找
                if not edge.get('condition') and not is_condition_connection:
                    status_res['status'] = 'warning'
                    status_res['message'] = f'An identical connection relationship [ {source_view_name} → {target_view_name} ] already exists.'
                    break
                # 自身为条件连接的情况，直接出 warning，然后跳出查找
                elif is_condition_connection:
                    status_res['status'] = 'warning'
                    status_res['message'] = f'An identical connection relationship [ {source_view_name} → {target_view_name} ] already exists.'
                    break
                # 先写入告警，但继续尝试看是否有报错的情况
                else:
                    status_res['status'] = 'warning'
                    status_res['message'] = f'An identical connection relationship [ {source_view_name} → {target_view_name} ] already exists.'
        return status_res

    
    def get_edge(self, edge_id):
        return find_by_attr(self._edges, 'id', edge_id)
    
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
                edge.get('condition') or None,
                edge.get('condition_detail') or None
            )
        return self

    def del_connection(self, source_chunk_id, target_chunk_id, source_handle=DEFAULT_OUTPUT_HANDLE_VALUE, target_handle=DEFAULT_INPUT_HANDLE_VALUE):
        """
        取消连线，分别输入：源节点id、目标节点id、源节点输出句柄（可选，默认为源节点的输出点）、目标节点的输入句柄（可选，默认为目标节点的输入点）
        """
        edges = []
        for edge in self._edges:
            if not (
                edge.get("source") == source_chunk_id and
                edge.get("target") == target_chunk_id and
                (source_handle is None or edge.get('source_handle') == source_handle) and
                (target_handle is None or edge.get('target_handle') == target_handle)
            ):
                edges.append(edge)
        # 有变更时赋值
        if len(edges) != len(self._edges):
            self._edges = edges
        return self
    
    def remove_all_connection(self):
        """移除所有连接关系，但保留注册"""
        self._edges = []
        return self

    def clone(self):
        return Schema(schema_data={
            "chunks": copy.deepcopy(self._chunks),
            "edges": copy.deepcopy(self._edges)
        })
