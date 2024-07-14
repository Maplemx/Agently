import base64
import sys
from .constants import EXECUTOR_TYPE_LOOP, EXECUTOR_TYPE_CONDITION

def draw_with_mermaid(schema_compiled_data):
    """使用 mermaid 绘制出图形，可点击 https://mermaid-js.github.io/mermaid-live-editor/edit 粘贴查看效果"""

    LOOP_CLASS_NAME = 'loop_style'
    CHUNK_CLASS_NAME = 'chunk_style'
    CONDITION_CLASS_NAME = 'condition_chunk_style'
    # 修复文本展示，避免特殊字符
    def fix_display_text(label: str):
        if not label:
            return label
        escaped_string = label.replace('"', '&quot;')
        return f'"{escaped_string}"'

    def to_node_symbol(chunk, title=None):
        chunk_name = title or fix_display_text(chunk["title"] or f'chunk-{chunk["id"]}' or 'Unknow chunk')
        # 条件节点，渲染成菱形
        if chunk.get('type') == EXECUTOR_TYPE_CONDITION:
            return f"{chunk['id']}" + "{{" + f"{chunk_name}" + "}}:::" + f"{CONDITION_CLASS_NAME}"
        return f"{chunk['id']}({chunk_name}):::{CHUNK_CLASS_NAME}"
    
    helper = { "loop_count": 0 }
    indent_str = '    '
    def generate_loop_body(chunk):
        """生成循环块"""
        loop_body = []
        # 判断 chunk 是否为子workflow，如果是，尝试绘制出来
        loop_info = (chunk.get('extra_info') or {}).get('loop_info') or {}
        if loop_info.get('type') == 'workflow':
            loop_body = generate_body(loop_info.get('detail'))
        else:
            loop_body.append(to_node_symbol(chunk, loop_info.get('detail')))

        # 生成唯一标题
        helper['loop_count'] += 1
        loop_title = f"Loop_{helper['loop_count']}"

        return {
            "title": loop_title,
            "body": [f"subgraph {loop_title}\n{indent_str}direction LR"] + loop_body + ["end"]
        }


    def generate_body(schema_data):
        """主体生成函数"""
        label_split = ' -->-- '
        condition_label_split = ' -- ◇ -- '
        edges = schema_data['edges']
        chunks = schema_data['chunks']
        chunk_map = {}
        for chunk in chunks:
            chunk_map[chunk['id']] = chunk
        graph_partial_list = []
        marked_loop_chunks = [] # 已被标记过的 loop chunk
        graph_loop_blocks = []
        exchanged_graph_symbol = {}
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

                # 判断是否是loop
                if target.get('type') == EXECUTOR_TYPE_LOOP:
                    # 如果未被处理过，则生成一个loop区域
                    if edge.get('target') not in marked_loop_chunks:
                        # 生成绘图数据
                        loop_graph_info = generate_loop_body(target)
                        # 加入节点
                        graph_loop_blocks.extend(loop_graph_info['body'])
                        # 标识已处理过
                        marked_loop_chunks.append(edge.get('target'))
                        # 登记该loop 节点信息，后续全重置连接到该循环节点
                        exchanged_graph_symbol[edge['target']] = loop_graph_info['title']
                # 处理本次连接标识
                full_labels_symbol = fix_display_text(
                    f"{start_label_symbol}{condition_label_split if condition_symbol else label_split}{end_label_symbol}")
                # 处理最终的起始节点
                latest_target_label = f"{exchanged_graph_symbol.get(edge['target'])}:::{LOOP_CLASS_NAME}" if exchanged_graph_symbol.get(
                    edge['target']) else to_node_symbol(target)
                latest_source_label = f"{exchanged_graph_symbol.get(edge['source'])}:::{LOOP_CLASS_NAME}" if exchanged_graph_symbol.get(
                    edge['source']) else to_node_symbol(source)
                # 加入绘制图中
                graph_partial_list.append(
                    f"{latest_source_label} -.-> |{full_labels_symbol}| {latest_target_label}")
        return graph_loop_blocks + graph_partial_list

    class_str = '\n'.join([
        f"classDef {CHUNK_CLASS_NAME} fill:#fbfcdb,stroke:#666,stroke-width:1px,color:#333;",
        f"classDef {CONDITION_CLASS_NAME} fill:#ECECFF,stroke:#9370DB,stroke-width:1px,color:#333;",
        f"classDef {LOOP_CLASS_NAME} fill:#f5f7fa,stroke:#666,stroke-width:1px,color:#333,stroke-dasharray: 5 5",
    ])
    return (
        "%%{ init: { 'flowchart': { 'curve': 'linear' }, 'theme': 'neutral' } }%%\n" +
        "%% Rendered By Agently %%\nflowchart LR\n" + class_str + "\n" +
        '\n'.join(map(lambda part: indent_str + part, generate_body(schema_compiled_data)))
    )

def draw_image_in_jupyter(schema_compiled_data):
    if 'IPython' in sys.modules:
        from IPython.display import Image, display
        mm_code = draw_with_mermaid(schema_compiled_data)
        graphbytes = mm_code.encode("utf8")
        base64_bytes = base64.b64encode(graphbytes)
        base64_string = base64_bytes.decode("ascii")
        display(Image(url="https://mermaid.ink/img/" + base64_string))
    else:
        print('Please use within the Jupyter environment.')
