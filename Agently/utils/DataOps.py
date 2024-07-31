import copy

class NamespaceOps(object):
    def __init__(self, namespace_name: str, data_ops: object, *, return_to: object=None):
        self.namespace_name = namespace_name
        self.data_ops = data_ops
        self.return_to = return_to if return_to else self

    def assign(self, input:any, desc: any=None):
        if input and desc == None:
            if isinstance(input, dict):
                return self.update(input)
            elif isinstance(input, list):
                return self.extend(input)
            else:
                return self.set(input)
        if input and desc != None:
            current_content = self.get(input)
            if isinstance(current_content, list):
                if isinstance(desc, list):
                    return self.extend(input, desc)
                else:
                    return self.append(input, desc)
            elif isinstance(desc, dict):
                return self.update(input, desc)
            else:
                return self.set(input, desc)


    def set(self, keys_with_dots: any, value: any=None):
        if value == None:
            self.data_ops.set(self.namespace_name, keys_with_dots)
        else:
            self.data_ops.set(f"{ self.namespace_name }.{ keys_with_dots }", value)
        return self.return_to

    def delta(self, keys_with_dots: str, value: any):
        if isinstance(value, dict):
            for k, v in value.items():
                self.delta(f"{ keys_with_dots }.{ k }", v)
        else:
            self.append(keys_with_dots, value)

    def append(self, keys_with_dots: any, value: any=None):
        if value == None:
            self.data_ops.append(self.namespace_name, keys_with_dots)
        else:
            self.data_ops.append(f"{ self.namespace_name }.{ keys_with_dots }", value)
        return self.return_to

    def extend(self, keys_with_dots: any, value: any=None):
        if value == None:
            self.data_ops.extend(self.namespace_name, keys_with_dots)
        else:
            self.data_ops.extend(f"{ self.namespace_name }.{ keys_with_dots }", value)
        return self.return_to

    def update(self, keys_with_dots: any, value: any=None):
        if value == None:
            self.data_ops.update(self.namespace_name, keys_with_dots)
        else:
            self.data_ops.update(f"{ self.namespace_name }.{ keys_with_dots }", value)
        return self.return_to
        
    def get(self, keys_with_dots: (str, None) = None, default = None, *, no_copy: bool = False):
        return self.data_ops.get(f"{ self.namespace_name }.{ keys_with_dots }" if keys_with_dots else self.namespace_name, default, no_copy = no_copy)

    def remove(self, keys_with_dots: str):
        return self.data_ops.remove(f"{ self.namespace_name }.{ keys_with_dots }")

    def empty(self):
        return self.data_ops.remove(self.namespace_name)

class DataOps(object):
    def __init__(self, *, target_data:dict=None, no_copy: bool=False):
        self.target_data = target_data or {}
        self.no_copy = no_copy

    def __locate_pointer(self, keys_with_dots: str):
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