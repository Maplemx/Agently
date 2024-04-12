def draw_with_mermaid(schema):
    """使用 mermaid 绘制出图形，可点击 https://mermaid-js.github.io/mermaid-live-editor/edit 粘贴查看效果"""
    edges = schema.edges
    chunks = schema.chunks
    chunk_map = {}
    for chunk in chunks:
        chunk_map[chunk['id']] = chunk

    # 修复文本展示，避免特殊字符
    def fix_display_text(label: str):
        if not label:
            return label
        escaped_string = label.replace('"', '&quot;')
        return f'"{escaped_string}"'

    def to_node_symbol(chunk):
        chunk_name = fix_display_text(chunk["title"] or f'chunk-{chunk["id"]}' or 'Unknow chunk')
        return f"{chunk['id']}({chunk_name})"


    graph_partial_list = []
    label_split = ' -->-- '
    condition_label_split = ' -- ◇ -- '
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

            full_labels_symbol = fix_display_text(
                f"{start_label_symbol}{condition_label_split if condition_symbol else label_split}{end_label_symbol}")
            graph_partial_list.append(
                f"{to_node_symbol(source)} -.-> |{full_labels_symbol}| {to_node_symbol(target)}")

    return (
        "%%{ init: { 'flowchart': { 'curve': 'linear' }, 'theme': 'neutral' } }%%\n" +
        "%% Rendered By Agently %%\nflowchart LR\n" +
        '\n'.join(map(lambda part: '    ' + part, graph_partial_list))
    )
