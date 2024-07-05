from ...lib.Store import Store

def condition_executor(inputs, store: Store, **sys_info):
    """条件执行器，会从其 extra_info['condition_info'] 中取到判断条件和结果符号，最终返回命中判断的结果符号，同时透传上游的值"""
    chunk_data = sys_info['chunk']['data']
    condition_info = (chunk_data.get('extra_info') or {}).get('condition_info') or {}
    normal_conditions = condition_info.get('conditions')
    # 从众多条件中依次判断，如果命中了，则返回对应条件的结果 id
    if normal_conditions and len(normal_conditions) > 0:
        for condition_desc in normal_conditions:
            condition = condition_desc.get('condition')
            if condition and condition(inputs['default'], store):
                return {
                    "condition_signal": condition_desc.get('condition_signal'),
                    "values": inputs['default']
                }
    # 否则返回 else 的结果 id
    else_condition = condition_info.get('else_condition')
    return {
        "condition_signal": else_condition.get('condition_signal'),
        "values": inputs['default']
    }
