def __inject_alias(targetClass, runtime_ctx_name, alias_dict, work_node_name, layer):
    for alias_type, alias_name in alias_dict.items():
        if alias_type == "get":
            setattr(targetClass, alias_name, lambda *, runtime_ctx_name=runtime_ctx_name: targetClass.get(runtime_ctx_name, target_runtime_ctx=layer))
        if alias_type == "set":
            setattr(targetClass, alias_name, lambda value, *, runtime_ctx_name=runtime_ctx_name: targetClass.set(runtime_ctx_name, value, target_runtime_ctx=layer))
        if alias_type == "set_kv":
            setattr(targetClass, alias_name, lambda item_key, item_value, *, runtime_ctx_name=runtime_ctx_name: targetClass.set(f"{ runtime_ctx_name }.{ item_key }", item_value, target_runtime_ctx=layer))
        if alias_type == "append":
            setattr(targetClass, alias_name, lambda value, *, runtime_ctx_name=runtime_ctx_name: targetClass.append(runtime_ctx_name, value, target_runtime_ctx=layer))
        if alias_type == "append_kv":
            setattr(targetClass, alias_name, lambda item_key, item_value, *, runtime_ctx_name=runtime_ctx_name: targetClass.append(f"{ runtime_ctx_name }.{ item_key }", item_value, target_runtime_ctx=layer))
        if alias_type == "extend":
            setattr(targetClass, alias_name, lambda value, *, runtime_ctx_name=runtime_ctx_name: targetClass.extend(runtime_ctx_name, value, target_runtime_ctx=layer))
        if alias_type == "customize":
            alias_func = alias_name["func"]
            alias_name = alias_name["name"]
            setattr(targetClass, alias_name, alias_func)
        alias_record = { alias_name: { "type": alias_type, "runtime_ctx_name": runtime_ctx_name, "work_node_name": work_node_name } }
        alias_records = targetClass.runtime_ctx.get("alias_records")
        alias_records = alias_records if alias_records else {}
        if alias_name in alias_records:
            if alias_records[alias_name]["type"] != alias_type or alias_records[alias_name]["runtime_ctx_name"] != runtime_ctx_name:
                raise AliasConflictException((alias_records[alias_name], alias_record))
        else:
            targetClass.runtime_ctx.update("alias_records", alias_record)
    return


def inject_alias(targetClass, layer):
    work_nodes = targetClass.runtime_ctx.get_all_above(domain = "work_nodes")
    if work_nodes == None:
        raise Exception("[init agent runtime_ctx]: No work node is stated. Use Agently/Blueprint.manage_work_node(<work_node_name>) to create one first.")
    for work_node_name, work_node in work_nodes.items():
        if "runtime_ctx_settings" in work_node:
            runtime_ctx_settings = work_node["runtime_ctx_settings"]
            for runtime_ctx_name in runtime_ctx_settings.keys():
                runtime_ctx_setting = runtime_ctx_settings[runtime_ctx_name]
                #confirm layer
                if "layer" in runtime_ctx_setting and runtime_ctx_setting["layer"] == layer:
                    #inject alias
                    if "alias" in runtime_ctx_setting:
                        __inject_alias(targetClass, runtime_ctx_name, runtime_ctx_setting["alias"], work_node_name, layer)

def set_default_runtime_ctx(target_runtime_ctx, layer):
    work_nodes = target_runtime_ctx.get_all_above(domain = "work_nodes")
    if work_nodes == None:
        raise Exception("[init agent runtime_ctx]: No work node is stated. Use Agently/Blueprint.manage_work_node(<work_node_name>) to create one first.")
    for work_node_name, work_node in work_nodes.items():
        if "runtime_ctx_settings" in work_node:
            runtime_ctx_settings = work_node["runtime_ctx_settings"]
            for runtime_ctx_name in runtime_ctx_settings.keys():
                runtime_ctx_setting = runtime_ctx_settings[runtime_ctx_name]
                #confirm layer
                if "layer" in runtime_ctx_setting and runtime_ctx_setting["layer"] == layer:
                    #set default value
                    if "default" in runtime_ctx_setting:
                        target_runtime_ctx.set(runtime_ctx_name, runtime_ctx_setting["default"])