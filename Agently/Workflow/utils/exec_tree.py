from ..Schema import Schema
from ..lib.constants import EXECUTOR_TYPE_NORMAL, EXECUTOR_TYPE_START, DEFAULT_INPUT_HANDLE_VALUE
import uuid

def generate_executed_schema(schema: dict):
    """根据定义描述，生成执行描述"""
    edges_map_info = generate_edge_prepare_data(schema.get('edges') or [])
    all_chunks = schema.get('chunks') or []

    def create_exec_chunk(chunk):
        next_chunks = []
        next_chunk_map = {}
        for target in edges_map_info['edges_target_map'].get(chunk['id'], []):
            target_id = target['target']
            next_chunk = next_chunk_map.get(target_id)
            # 如之前没存入，则新建
            if not next_chunk:
                next_chunk = {
                    'id': target_id,
                    'handles': []
                }
                next_chunks.append(next_chunk)
                next_chunk_map[next_chunk['id']] = next_chunk
            # 往 chunk 中注入当前的 handle
            next_chunk['handles'].append({
                'handle': target['target_handle'],
                'source_handle': target['source_handle'],
                'condition': target.get('condition') or None
            })
                
        hanldes_desc = chunk.get('handles') or {}
        inputs_desc = hanldes_desc.get('inputs') or []
        if not len(inputs_desc):
            inputs_desc = [{'handle': DEFAULT_INPUT_HANDLE_VALUE}]
        return {
            'id': chunk['id'],
            'loop_entry': False, # 是否是循环的起点
            'next_chunks': next_chunks,
            'type': chunk.get('type') or EXECUTOR_TYPE_NORMAL,
            'executor': chunk.get('executor'),
            'deps': [
                {
                    'handle': input_desc.get('handle'),
                    # 运行时的依赖值，会随运行时实时更新，初始尝试从定义中取默认值
                    'data_slots': [{
                        'id': str(uuid.uuid4()), # 唯一 id，设置后就不变了，用于标识管理
                        'is_ready': True,
                        'execution_ticket': str(uuid.uuid4()), # 可执行票据，可派发
                        'updator': 'default', # 更新者
                        'value': input_desc.get('default')
                    }] if (input_desc.get('default') != None) or (chunk.get('type') == EXECUTOR_TYPE_START) else []
                }
                for input_desc in inputs_desc
            ],
            'data': chunk
        }
    
    runtime_chunks_map = {}
    for chunk in all_chunks:
        runtime_chunks_map[chunk['id']] = create_exec_chunk(chunk)
    
    # 标识循环起点
    def update_loop_walker(chunk, paths = []):
        for next_info in chunk.get('next_chunks'):
            next_chunk = runtime_chunks_map.get(next_info['id'])
            if next_chunk:
                if next_chunk['id'] in paths:
                    next_chunk['loop_entry'] = True
                    return
                update_loop_walker(next_chunk, paths + [next_chunk['id']])

    entries = []
    for chunk in all_chunks:
        if not edges_map_info['edges_source_map'].get(chunk['id'], []):
            entry_chunk = runtime_chunks_map.get(chunk['id'])
            if entry_chunk:
                entries.append(entry_chunk)
                update_loop_walker(entry_chunk, [entry_chunk['id']])

    return {
        'entries': entries,
        'chunk_map': runtime_chunks_map
    }

def create_empty_data_slot(chunk):
    return {
        'is_ready': chunk.get('type') == EXECUTOR_TYPE_START,
        'updator': '',
        'value': None
    }

def create_empty_data_slots(chunk):
    return [{
        'is_ready': True,
        'updator': '',
        'value': None
    }] if chunk.get('type') == EXECUTOR_TYPE_START else []

def reset_chunk_slot_val(slot):
    """清空掉某个dep slot 的值"""
    slot['value'] = None
    slot['is_ready'] = False
    slot['execution_ticket'] = ''
    slot['updator'] = ''

def disable_chunk_dep_ticket(slot):
    """回收执行票据"""
    slot['execution_ticket'] = ''

def create_new_chunk_slot_with_val(ref_chunk_id, new_val):
    """创建一个新的带有值的slot"""
    return {
        'id': str(uuid.uuid4()), # 唯一 id，设置后就不变了，用于标识管理
        'is_ready': True,
        'execution_ticket': str(uuid.uuid4()), # 可执行票据，可派发
        'updator': ref_chunk_id, # 更新者
        'value': new_val
    }

def generate_edge_prepare_data(edges: list):
    edges_target_map = {}
    edges_source_map = {}

    for edge in edges:
        edges_target_map.setdefault(edge['source'], []).append(edge)
        edges_source_map.setdefault(edge['target'], []).append(edge)

    return {
        'edges_source_map': edges_source_map,
        'edges_target_map': edges_target_map
    }
