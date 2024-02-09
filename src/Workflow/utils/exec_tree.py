from ..Schema import Schema
from .find import find_by_attr

def prepare_data(schema: Schema):
    edges_target_map = {}
    edges_source_map = {}
    edges = schema.edges

    # Step 1. 处理得到原始数据
    for edge in edges:
        edges_target_map.setdefault(edge['source'], []).append(edge)
        edges_source_map.setdefault(edge['target'], []).append(edge)

    # Step 2. 进一步处理数据
    full_logic_tree = []

    def build_logic_nodes(current_item, paths = []):
        targets = edges_target_map.get(current_item['id'], [])
        branches = []
        current_branch_recorder = {}
        for target in targets:
            node_id = target['target']
            if node_id not in current_branch_recorder:
                target_chunk = (schema.get_chunk(node_id) or {})
                branch = {
                    'id': node_id,
                    'executor': target_chunk.get('executor'),
                    'data': target_chunk,
                    'point_type': 'end' if not edges_target_map.get(node_id) else 'normal'
                }
                # 循环依赖的节点需要特殊处理
                if len(paths) > 0 and branch['id'] in paths:
                    branches.append({
                        **branch,
                        'branches': [],
                        'point_type': 'loop'
                    })
                    break
                current_branch_recorder[node_id] = branch
                new_paths = paths.copy()
                new_paths.append(current_item['id'])
                branch['branches'] = build_logic_nodes(branch, new_paths)
                branches.append(branch)
        return branches

    for node in schema.chunks:
        if not edges_source_map.get(node['id'], []):
            root_logic_node = {
                'id': node['id'],
                'executor': node.get('executor'),
                'data': node,
                'point_type': 'start'
            }
            root_logic_node['branches'] = build_logic_nodes(root_logic_node, [])
            full_logic_tree.append(root_logic_node)

    return {
        'edges_source_map': edges_source_map,
        'full_logic_tree': full_logic_tree
    }

def extract_default_dep_data(chunk, handle_name: str):
    """从 chunk 中摘出默认的值（基于其 handle 设置）"""
    output_handles = (chunk.get('handles') or {}).get('outputs')
    if not output_handles or len(output_handles) == 0:
        return None
    target_handle = find_by_attr(output_handles, 'handle', handle_name)
    if target_handle and 'default' in target_handle:
        return target_handle['default']
    return None

def generate_exec_tree(schema: Schema):
    prepared_data = prepare_data(schema)

    def create_exec_tree_node(node):
        return {
            'id': node['id'],
            'deps': [
                {
                    'id': dep['source'],
                    'handler': dep['source_handle'],
                    'target_handler': dep['target_handle'],
                    'condition': dep.get('condition') or None,
                    'default_data': extract_default_dep_data(schema.get_chunk(dep['source']), dep['source_handle'])
                } for dep in prepared_data['edges_source_map'].get(node['id'], [])
            ],
            'data': node['data'],
            'executor': node['executor'],
            'point_type': node['point_type'], # 类型，包含 start/end/loop/normal
            'branches': []
        }

    exec_tree = []

    def logic_tree_walker(nodes, parent_collections):
        for node in nodes:
            exec_tree_node = create_exec_tree_node(node)
            parent_collections.append(exec_tree_node)
            if node.get('branches') and node['branches']:
                logic_tree_walker(node['branches'], exec_tree_node['branches'])

    logic_tree_walker(prepared_data['full_logic_tree'], exec_tree)
    return exec_tree
