import copy

class StorageEditor(object):
    def __init__(
            self,
            *,
            target_data: dict=None,
            no_copy: bool=False,
            get_target_data: callable,
            storage: object,
            table_name: str
        ):
        self.target_data = target_data
        self.no_copy = no_copy
        self.get_target_data = get_target_data
        self.storage = storage
        self.table_name = table_name

    def __locate_pointer(self, keys_with_dots: str):
        if self.target_data == None:
            self.target_data = self.get_target_data() or {}
        keys = keys_with_dots.split('.')
        pointer = self.target_data
        current_key = None
        for key in keys:
            if current_key:
                pointer = pointer[current_key]
            current_key = key
            if key not in pointer:
                pointer[key] = {}
        return pointer, current_key

    def set(self, keys_with_dots: str, value: any):
        pointer, key = self.__locate_pointer(keys_with_dots)
        pointer[key] = value
        return self

    def delta(self, keys_with_dots: str, value: any):
        if isinstance(value, dict):
            for k, v in value.items():
                self.delta(f"{ keys_with_dots }.{ k }", v)
        else:
            if self.get(keys_with_dots):
                self.append(keys_with_dots, value)
            else:
                self.set(keys_with_dots, value)

    def append(self, keys_with_dots: str, value: any):
        pointer, key = self.__locate_pointer(keys_with_dots)
        if isinstance(pointer[key], list):
            pointer[key].append(value)
        elif pointer[key] == {}:
            pointer[key] = []
            pointer[key].append(value)
        else:
            pointer[key] = [pointer[key]]
            pointer[key].append(value)
        return self

    def extend(self, keys_with_dots: str, value: any):
        if not isinstance(value, list):
            value = [value]
        pointer, key = self.__locate_pointer(keys_with_dots)
        if isinstance(pointer[key], list):
            pointer[key].extend(value)
        elif pointer[key] == {}:
            pointer[key] = []
            pointer[key].extend(value)
        else:
            pointer[key] = [pointer[key]]
            pointer[key].extend(value)
        return self 

    def __update_dict(self, pointer: dict, pointer_key: str, dict_item: any):
        if isinstance(dict_item, dict):
            for key in dict_item.keys():
                if key not in pointer[pointer_key]:
                    pointer[pointer_key][key] = {}
                if isinstance(dict_item[key], dict):
                    self.__update_dict(pointer[pointer_key], key, dict_item[key])
                else:
                    if dict_item[key] != None:
                        pointer[pointer_key][key] = dict_item[key]
        else:
            if dict_item != None:
                pointer[pointer_key] = dict_item

    def update(self, keys_with_dots: str, value: any):
        pointer, key = self.__locate_pointer(keys_with_dots)
        self.__update_dict(pointer, key, value)
        return self

    def update_by_dict(self, data_dict: dict):
        for key, value in data_dict.items():
            self.update(key, value)
        return self

    def _deep_get(self, data):
        result = None
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                result.update({ key: self._deep_get(data[key]) })
            return result
        elif isinstance(data, list):
            result = []
            for item in data:
                result.append(self._deep_get(item))
            return result
        elif isinstance(data, set):
            result = set()
            for item in list(data):
                result.add(self._deep_get(item))
            return result
        elif isinstance(data, tuple):
            result = []
            for item in list(data):
                result.append(self._deep_get(item))
            return tuple(result)
        elif hasattr(data, '__class__') and hasattr(data, '__module__') and data.__module__ != 'builtins':
            return data
        else:
            return copy.deepcopy(data)

    def get(self, keys_with_dots: (str, None) = None, default: str=None, *, no_copy: bool = False):
        if self.target_data == None:
            self.target_data = self.get_target_data() or {}
        if keys_with_dots:
            keys = keys_with_dots.split('.')
            pointer = self.target_data
            for key in keys:
                if key not in pointer:
                    return default
                else:
                    pointer = pointer[key]
            if self.no_copy or no_copy:
                return pointer
            else:
                if hasattr(pointer, '__class__') and hasattr(pointer, '__module__') and pointer.__module__ != 'builtins':
                    return pointer
                else:
                    try:
                        return copy.deepcopy(pointer)
                    except TypeError:
                        return self._deep_get(pointer)
        else:
            if self.no_copy or no_copy:
                return self.target_data
            else:
                if hasattr(self.target_data, '__class__') and hasattr(self.target_data, '__module__') and self.target_data.__module__ != 'builtins':
                    return self.target_data
                else:
                    try:
                        return copy.deepcopy(self.target_data)
                    except TypeError:
                        return self.target_data

    def remove(self, keys_with_dots: str):
        pointer, key = self.__locate_pointer(keys_with_dots)
        del pointer[key]
        return self

    def empty(self):
        self.target_data = {}
        return self

    def save(self):
        final_data = self.get()
        return self.storage.set_all(self.table_name, final_data)

"""
class StorageEditor(DataOps):
    def __init__(self, target_data: (dict, None), *, storage: object, table_name: str):
        self.storage = storage
        self.table_name = table_name
        super().__init__(target_data = target_data)

    def save(self):
        final_data = self.get()
        return self.storage.set_all(self.table_name, final_data)
"""
        
class StorageDelegate(object):
    def __init__(self, *, db_name: str = "default", plugin_manager: object, settings: object):
        self.db_name = db_name
        self.plugin_manager = plugin_manager
        self.settings = settings
        return

    def set_storage_type(self, storage_type: str):
        self.settings.set("storage_type", storage_type)
        return self

    def __get_storage_plugin(self):
        storage_type = self.settings.get_trace_back("storage_type")
        return self.plugin_manager.get("storage", storage_type)(db_name = self.db_name, settings = self.settings)

    def set(self, table_name: str, key: str, value: any):
        self.__get_storage_plugin().set(table_name, key, value)
        return self

    def set_all(self, table_name: str, full_data: dict):
        self.__get_storage_plugin().set_all(table_name, full_data)
        return self

    def remove(self, table_name: str, key: str):
        self.__get_storage_plugin().remove(table_name, key)
        return self

    def update(self, table_name:str, update_data: dict):
        self.__get_storage_plugin().update(table_name, update_data)
        return self

    def get(self, table_name: str, key: str):
        return self.__get_storage_plugin().get(table_name, key)

    def get_all(self, table_name: str, keys: (list, None)=None):
        return self.__get_storage_plugin().get_all(table_name, keys)

    def table(self, table_name: str):
        get_table_data = lambda: self.get_all(table_name)
        return StorageEditor(get_target_data = get_table_data, storage = self, table_name = table_name)