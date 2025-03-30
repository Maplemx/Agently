import copy
from typing import Any, Dict, List, Optional, Union


class NamespaceOps:
    def __init__(self, namespace_name: str, data_ops: 'DataOps', *, return_to: Optional[Any] = None):
        self.namespace_name = namespace_name
        self.data_ops = data_ops
        self.return_to = return_to if return_to else self

    def assign(self, input: Any, desc: Any = None) -> 'NamespaceOps':
        """智能分配值，根据输入类型自动选择合适的方法"""
        if desc is None:
            if isinstance(input, dict):
                return self.update(input)
            elif isinstance(input, list):
                return self.extend(input)
            else:
                return self.set(input)
        else:
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

    def set(self, keys_with_dots: Any, value: Any = None) -> 'NamespaceOps':
        """设置键值对"""
        if value is None:
            self.data_ops.set(self.namespace_name, keys_with_dots)
        else:
            self.data_ops.set(f"{self.namespace_name}.{keys_with_dots}", value)
        return self.return_to

    def delta(self, keys_with_dots: str, value: Any) -> None:
        """递归处理差异更新"""
        if isinstance(value, dict):
            for k, v in value.items():
                self.delta(f"{keys_with_dots}.{k}", v)
        else:
            self.append(keys_with_dots, value)

    def append(self, keys_with_dots: Any, value: Any = None) -> 'NamespaceOps':
        """追加值到列表"""
        if value is None:
            self.data_ops.append(self.namespace_name, keys_with_dots)
        else:
            self.data_ops.append(f"{self.namespace_name}.{keys_with_dots}", value)
        return self.return_to

    def extend(self, keys_with_dots: Any, value: Any = None) -> 'NamespaceOps':
        """扩展列表"""
        if value is None:
            self.data_ops.extend(self.namespace_name, keys_with_dots)
        else:
            self.data_ops.extend(f"{self.namespace_name}.{keys_with_dots}", value)
        return self.return_to

    def update(self, keys_with_dots: Any, value: Any = None) -> 'NamespaceOps':
        """更新字典"""
        if value is None:
            self.data_ops.update(self.namespace_name, keys_with_dots)
        else:
            self.data_ops.update(f"{self.namespace_name}.{keys_with_dots}", value)
        return self.return_to
        
    def get(self, keys_with_dots: Optional[str] = None, default: Any = None, *, no_copy: bool = False) -> Any:
        """获取值"""
        key = f"{self.namespace_name}.{keys_with_dots}" if keys_with_dots else self.namespace_name
        return self.data_ops.get(key, default, no_copy=no_copy)

    def remove(self, keys_with_dots: str) -> Any:
        """删除键"""
        return self.data_ops.remove(f"{self.namespace_name}.{keys_with_dots}")

    def empty(self) -> Any:
        """清空命名空间"""
        return self.data_ops.remove(self.namespace_name)


class DataOps:
    def __init__(self, *, target_data: Optional[Dict] = None, no_copy: bool = False):
        self.target_data: Dict = target_data or {}
        self.no_copy = no_copy

    def __locate_pointer(self, keys_with_dots: str) -> tuple:
        """定位到目标字典和最终键"""
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

    def set(self, keys_with_dots: str, value: Any) -> 'DataOps':
        """设置值"""
        pointer, key = self.__locate_pointer(keys_with_dots)
        pointer[key] = value
        return self

    def delta(self, keys_with_dots: str, value: Any) -> None:
        """增量更新，递归处理嵌套字典"""
        if isinstance(value, dict):
            for k, v in value.items():
                self.delta(f"{keys_with_dots}.{k}", v)
        else:
            if self.get(keys_with_dots):
                self.append(keys_with_dots, value)
            else:
                self.set(keys_with_dots, value)

    def __prepare_list_for_append(self, pointer: Dict, key: str) -> None:
        """准备列表以供追加"""
        if not isinstance(pointer[key], list):
            if pointer[key] == {}:
                pointer[key] = []
            else:
                pointer[key] = [pointer[key]]

    def append(self, keys_with_dots: str, value: Any) -> 'DataOps':
        """追加值到列表"""
        pointer, key = self.__locate_pointer(keys_with_dots)
        self.__prepare_list_for_append(pointer, key)
        pointer[key].append(value)
        return self

    def extend(self, keys_with_dots: str, value: Any) -> 'DataOps':
        """扩展列表"""
        if not isinstance(value, list):
            value = [value]
            
        pointer, key = self.__locate_pointer(keys_with_dots)
        self.__prepare_list_for_append(pointer, key)
        pointer[key].extend(value)
        return self

    def __update_dict(self, pointer: Dict, pointer_key: str, dict_item: Any) -> None:
        """递归更新字典"""
        if isinstance(dict_item, dict):
            for key in dict_item:
                if key not in pointer[pointer_key]:
                    pointer[pointer_key][key] = {}
                    
                if isinstance(dict_item[key], dict):
                    self.__update_dict(pointer[pointer_key], key, dict_item[key])
                elif dict_item[key] is not None:
                    pointer[pointer_key][key] = dict_item[key]
        elif dict_item is not None:
            pointer[pointer_key] = dict_item

    def update(self, keys_with_dots: str, value: Any) -> 'DataOps':
        """更新字典"""
        pointer, key = self.__locate_pointer(keys_with_dots)
        self.__update_dict(pointer, key, value)
        return self

    def update_by_dict(self, data_dict: Dict) -> 'DataOps':
        """通过字典批量更新"""
        for key, value in data_dict.items():
            self.update(key, value)
        return self

    def _deep_get(self, data: Any) -> Any:
        """深度复制数据，处理特殊类型"""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                result[key] = self._deep_get(value)
            return result
        elif isinstance(data, list):
            return [self._deep_get(item) for item in data]
        elif isinstance(data, set):
            return {self._deep_get(item) for item in data}
        elif isinstance(data, tuple):
            return tuple(self._deep_get(item) for item in data)
        elif hasattr(data, '__class__') and hasattr(data, '__module__') and data.__module__ != 'builtins':
            return data
        else:
            return copy.deepcopy(data)

    def get(self, keys_with_dots: Optional[str] = None, default: Any = None, *, no_copy: bool = False) -> Any:
        """获取值，支持点分隔路径"""
        # 处理空键情况
        if not keys_with_dots:
            return self._handle_copy(self.target_data, no_copy)
            
        # 查找路径
        keys = keys_with_dots.split('.')
        pointer = self.target_data
        
        for key in keys:
            if key not in pointer:
                return default
            pointer = pointer[key]
            
        return self._handle_copy(pointer, no_copy)
    
    def _handle_copy(self, data: Any, no_copy: bool) -> Any:
        """根据复制标志处理数据复制"""
        if self.no_copy or no_copy:
            return data
            
        if hasattr(data, '__class__') and hasattr(data, '__module__') and data.__module__ != 'builtins':
            return data
            
        try:
            return copy.deepcopy(data)
        except TypeError:
            return self._deep_get(data)

    def remove(self, keys_with_dots: str) -> 'DataOps':
        """删除指定键"""
        pointer, key = self.__locate_pointer(keys_with_dots)
        del pointer[key]
        return self

    def empty(self) -> 'DataOps':
        """清空所有数据"""
        self.target_data = {}
        return self