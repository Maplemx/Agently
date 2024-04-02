import yaml
from .preset_chunks import preset_chunks

def create_chunk_with_executor(workflow, chunk_id, chunk_info, chunk_executor):
    workflow.chunk(chunk_id=chunk_id, **chunk_info)(chunk_executor)

def start_yaml(workflow, yaml_dict, *, draw):
    # Check Essential Items
    if "chunks" not in yaml_dict or "connections" not in yaml_dict:
        raise Exception("Workflow YAML must include item 'chunks' and item 'connections'.")
    # Create Chunks
    for chunk_id, chunk_info in yaml_dict["chunks"].items():
        chunk_type = None
        chunk_executor_name = None
        created = False
        # Check Chunk Info Format
        if not isinstance(chunk_info, dict):
            raise Exception(f"Content of chunk '{ chunk_id }' should be a dict.")
        # Type Stated
        if "type" in chunk_info:
            chunk_type = chunk_info["type"]
            if chunk_type in preset_chunks["type_list"]:
                preset_chunks["create"][chunk_info["type"]](workflow, chunk_id, chunk_info)
                created = True
        # Executor Stated
        if "executor" in chunk_info:
            chunk_executor_name = chunk_info["executor"]
            chunk_executor = workflow.executor_manager.get(chunk_executor_name)
            if chunk_executor:
                create_chunk_info = chunk_info.copy()
                del create_chunk_info["executor"]
                create_chunk_with_executor(workflow, chunk_id, create_chunk_info, chunk_executor)
                created = True
            else:
                raise Exception(f"Can not find registered chunk executor named '{ chunk_executor_name }'.")
        # Can Not Create Chunk
        if not created:
            raise Exception(f"Can not create chunk: \nChunk type: { chunk_type }\nExecutor name: { chunk_executor_name }")
    # State Connections
    for connection in yaml_dict["connections"]:
        from_chunk_id = None
        to_chunk_id = None
        from_chunk_handle = None
        to_chunk_handle = None
        # full expression
        if isinstance(connection, dict):
            if "from" not in connection:
                raise Exception(f"Must state origin chunk id in key 'from'.\nConnection: { str(connection) }")
            if "to" not in connection:
                raise Exception(f"Must state target chunk id in key 'to'.\nConnection: { str(connection) }")
            from_info_list = connection["from"].split(".")
            from_chunk_id = from_info_list[0]
            from_chunk_handle = from_info_list[1] if len(from_info_list) > 1 else None
            to_info_list = connection["to"].split(".")
            to_chunk_id = to_info_list[0]
            to_chunk_handle = to_info_list[1] if len(to_info_list) > 1 else None
            from_chunk = (
                workflow.chunks[from_chunk_id].handle(from_chunk_handle)
                if from_chunk_handle
                else workflow.chunks[from_chunk_id]
            )
            to_chunk = (
                workflow.chunks[to_chunk_id].handle(to_chunk_handle)
                if to_chunk_handle
                else workflow.chunks[to_chunk_id]
            )
            from_chunk.connect_to(to_chunk)
        # simple expression
        elif isinstance(connection, str):
            connection_info_list = connection.split("->")
            if len(connection_info_list) < 2:
                raise Exception(f"Connect chunk id with at least one '->'.\nConnection: { connection }")
            from_chunk_id = None
            from_chunk_handle = None
            to_chunk_id = None
            to_chunk_handle = None
            is_first_chunk = True
            for connection_chunk in connection_info_list:
                connection_chunk_info_list = connection_chunk.split(".")
                connection_chunk_id = connection_chunk_info_list[0]
                connection_chunk_handle = connection_info_list[1] if len(connection_chunk_info_list) > 1 else None
                if is_first_chunk:
                    from_chunk_id = connection_chunk_id
                    from_chunk_handle = connection_chunk_handle
                    is_first_chunk = False
                else:
                    to_chunk_id = connection_chunk_id
                    to_chunk_handle = connection_chunk_handle
                    from_chunk = (
                        workflow.chunks[from_chunk_id].handle(from_chunk_handle)
                        if from_chunk_handle
                        else workflow.chunks[from_chunk_id]
                    )
                    to_chunk = (
                        workflow.chunks[to_chunk_id].handle(to_chunk_handle)
                        if to_chunk_handle
                        else workflow.chunks[to_chunk_id]
                    )
                    from_chunk.connect_to(to_chunk)
                    from_chunk_id = to_chunk_id
                    from_chunk_handle = to_chunk_handle
    # Start Workflow
    if draw:
        return workflow.draw()
    else:
        return workflow.start()

def start_yaml_from_path(workflow, yaml_path, *, draw):
    try:
        with open(yaml_path, "r") as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
            return start_yaml(workflow, yaml_dict, draw=draw)
    except Exception as e:
        raise Exception(f"[Agently Workflow] Error occured when start YAML from path '{ yaml_path }'.\nError: { str(e) }")

def start_yaml_from_str(workflow, yaml_str, *, draw):
    try:
        yaml_dict = yaml.safe_load(yaml_str)
        return start_yaml(workflow, yaml_dict, draw=draw)
    except Exception as e:
        raise Exception(f"[Agently Workflow] Error occured when start YAML from string:\n{ yaml_str }\nError: { str(e) }")