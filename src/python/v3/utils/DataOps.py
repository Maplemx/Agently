import copy

class NamespaceOps(object):
    def __init__(self, namespace_name: str, data_ops: object, *, return_to: object=None):
        self.namespace_name = namespace_name
        self.data_ops = data_ops
        self.return_to = return_to if return_to else self

    def assign(self, input_key:any, input_content: any=None):
        if input_key and input_content == None:
            if isinstance(input_key, dict):
                return self.update(input_key)
            elif isinstance(input_key, list):
                return self.extend(input_key)
            else:
                return self.set(input_key)
        if input_key and input_content != None:
            current_content = self.get(input_key)
            if isinstance(current_content, list):
                if isinstance(input_content, list):
                    return self.extend(input_key, input_content)
                else:
                    return self.append(input_key, input_content)
            elif isinstance(input_content, dict):
                return self.update(input_key, input_content)
            else:
                return self.set(input_key, input_content)


    def set(self, keys_with_dots: any, value: any=None):
        if not value:
            self.data_ops.set(self.namespace_name, keys_with_dots)
        else:
            self.data_ops.set(f"{ self.namespace_name }.{ keys_with_dots }", value)
        return self.return_to

    def append(self, keys_with_dots: any, value: any=None):
        if not value:
            self.data_ops.append(self.namespace_name, keys_with_dots)
        else:
            self.data_ops.append(f"{ self.namespace_name }.{ keys_with_dots }", value)
        return self.return_to

    def extend(self, keys_with_dots: any, value: any=None):
        if not value:
            self.data_ops.extend(self.namespace_name, keys_with_dots)
        else:
            self.data_ops.extend(f"{ self.namespace_name }.{ keys_with_dots }", value)
        return self.return_to

    def update(self, keys_with_dots: any, value: any=None):
        if not value:
            self.data_ops.update(self.namespace_name, keys_with_dots)
        else:
            self.data_ops.update(f"{ self.namespace_name }.{ keys_with_dots }", value)
        return self.return_to
        
    def get(self, keys_with_dots: (str, None) = None):
        return self.data_ops.get(f"{ self.namespace_name }.{ keys_with_dots }" if keys_with_dots else self.namespace_name)

class DataOps(object):
    def __init__(self, *, target_data: (dict, None), no_copy: bool=False):
        if target_data == None:
            target_data = {}
        self.target_data = target_data
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

    def get(self, keys_with_dots: (str, None) = None):
        if keys_with_dots:
            keys = keys_with_dots.split('.')
            pointer = self.target_data
            for key in keys:
                if key not in pointer:
                    return None
                else:
                    pointer = pointer[key]
            if self.no_copy:
                return pointer
            else:
                return copy.deepcopy(pointer)
        else:
            if self.no_copy:
                return self.target_data
            else:
                return copy.deepcopy(self.target_data)

    def empty(self):
        self.target_data = {}
        return self