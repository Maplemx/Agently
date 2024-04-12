import os
import importlib

def scan():
    type_list = []
    create_dict = {}
    dir_path = os.path.dirname(os.path.abspath(__file__))
    for item in os.listdir(dir_path):
        if item.endswith(".py") and item != "__init__.py":
            chunk_type_name = item[:-3]
            type_list.append(chunk_type_name)
            preset_chunk = importlib.import_module(f".{ chunk_type_name }", package = __package__)
            if not hasattr(preset_chunk, "create"):
                raise Exception(f"Preset chunk '{ chunk_type_name }' must state a `create()` function.")
            create_dict.update({ chunk_type_name: getattr(preset_chunk, "create") })
    return {
        "type_list": type_list,
        "create": create_dict,
    }

preset_chunks = scan()