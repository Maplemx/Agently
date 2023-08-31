import copy

class RuntimeCtx(object):
    def __init__ (self, father = None, init_data = {}, **kwargs):
        self.default_domain = kwargs.get("domain", "default")
        self.father = father
        self.runtime_ctx_data = init_data.copy()
        return

    def __update_dict(self, target, dict_item):
        for key in dict_item.keys():
            if key not in target:
                target[key] = {}
            if isinstance(dict_item[key], dict):
                self.__update_dict(target[key], dict_item[key])
            else:
                if dict_item[key] != None:
                    target[key] = dict_item[key]

    def __action(self, action_name, target, keys, value):
        if len(keys) == 1:
            if action_name == "set":
                target.update({ keys[0]: value })
            if action_name == "append":
                key = keys[0]
                if key not in target:
                    target[key] = [value]
                else:
                    target[key].append(value)
            if action_name == "extend":
                key = keys[0]
                if key not in target or not isinstance(target[key], list):
                    target[key] = value
                else:
                    target[key].extend(value)
            if action_name == "add":
                key = keys[0]
                if key not in target:
                    target[key] = set([value])
                else:
                    target[key].add(value)
            if action_name == "update":
                key = keys[0]
                if key not in target:
                    if value != None:
                        target[key] = value
                else:
                    if isinstance(value, dict):
                        self.__update_dict(target[key], value)
                    else:
                        if value != None:
                            target.update({ key: value })
        else:
            key = keys[0]
            if key not in target:
                target[key] = {}
            self.__action(action_name, target[key], keys[1:], value)
        return

    def _action(self, action_name, keys, value, **kwargs):
        domain = kwargs.get("domain", self.default_domain)
        if domain not in self.runtime_ctx_data:
            self.runtime_ctx_data[domain] = {}
        splited_keys = keys.split('.')
        value = copy.deepcopy(value)
        self.__action(action_name, self.runtime_ctx_data[domain], splited_keys, value)
        return

    def set(self, keys, value, **kwargs):
        self._action("set", keys, value, **kwargs)
        return self

    def append(self, keys, value, **kwargs):
        self._action("append", keys, value, **kwargs)
        return self

    def extend(self, keys, value, **kwargs):
        self._action("extend", keys, value, **kwargs)
        return self

    def add(self, keys, value, **kwargs):
        self._action("add", keys, value, **kwargs)
        return self

    def update(self, keys, value, **kwargs):
        self._action("update", keys, value, **kwargs)
        return self
    
    def set_all(self, data, **kwargs):
        domain = kwargs.get("domain", self.default_domain)
        data = copy.deepcopy(data)
        self.runtime_ctx_data.update({ domain: data })
        return self

    def clear(self, **kwargs):
        domain = kwargs.get("domain", self.default_domain)
        self.runtime_ctx_data.update({ domain: {} })
        return self

    def get(self, key, **kwargs):
        domain = kwargs.get("domain", self.default_domain)
        if domain in self.runtime_ctx_data and key in self.runtime_ctx_data[domain]:
            return copy.deepcopy(self.runtime_ctx_data[domain][key])
        else:
            return None if self.father == None else copy.deepcopy(self.father.get(key, domain = domain))

    def get_all(self, **kwargs):
        domain = kwargs.get("domain", self.default_domain)
        #return copy.deepcopy(self.runtime_ctx_data[domain]) if domain in self.runtime_ctx_data else None
        return copy.deepcopy(self.runtime_ctx_data[domain]) if domain in self.runtime_ctx_data else None

    def __get_father_list(self, target, current_list):
        if target.father != None:
            current_list.append(target)
            return self.__get_father_list(target.father, current_list)
        else:
            current_list.append(target)
            return current_list

    def get_all_above(self, **kwargs):
        domain = kwargs.get("domain", self.default_domain)
        father_list = self.__get_father_list(self, [])
        reverse_list = father_list[::-1]
        result = {}
        for target in father_list:
            target_all_dict = target.get_all(domain=domain)
            target_all_dict = target_all_dict if target_all_dict else {}
            self.__update_dict(result, target_all_dict)
        return copy.deepcopy(result)

    def get_all_domain (self):
        return copy.deepcopy(self.runtime_ctx_data)