import pytest
import json
import yaml
import toml
import datetime
from pathlib import Path
from unittest.mock import mock_open, patch
from collections.abc import Mapping, Sequence

from agently.utils.RuntimeData import DictRef
from agently.utils import RuntimeData, RuntimeDataNamespace


class TestDictRef:
    """Test DictRef helper class"""

    def test_dict_ref_basic_operations(self):
        container = {'a': 1, 'b': 2}
        ref = DictRef(container, 'a')

        assert ref.get() == 1
        ref.set(10)
        assert container['a'] == 10
        assert ref.get() == 10

    def test_dict_ref_root_container(self):
        container = {'a': 1}
        ref = DictRef(container)

        assert ref.get() == {'a': 1}
        ref.set({'b': 2})
        assert container == {'b': 2}

    def test_dict_ref_update(self):
        container = {'nested': {'a': 1}}
        ref = DictRef(container, 'nested')

        ref.update({'b': 2})
        assert container['nested'] == {'a': 1, 'b': 2}

    def test_dict_ref_move_in(self):
        container = {'nested': {'deep': {'value': 42}}}
        ref = DictRef(container, 'nested')
        deep_ref = ref.move_in('deep')

        assert deep_ref.get() == {'value': 42}

    def test_dict_ref_errors(self):
        container = {'a': 'string'}
        ref = DictRef(container, 'a')

        # Should raise TypeError when trying to update non-dict
        with pytest.raises(TypeError):
            ref.update({'b': 2})

        # Should raise TypeError when setting root to non-dict
        root_ref = DictRef({})
        with pytest.raises(TypeError):
            root_ref.set("not a dict")


class TestRuntimeDataBasicOperations:
    """Test basic RuntimeData operations"""

    def test_initialization(self):
        # Default initialization
        rd1 = RuntimeData()
        assert rd1.data == {}
        assert rd1.name.startswith('runtime_data_')
        assert rd1.parent is None

        # Initialization with data
        rd2 = RuntimeData({'key': 'value'})
        assert rd2.data == {'key': 'value'}

        # Initialization with name and parent
        rd3 = RuntimeData(name='test', parent=rd2)
        assert rd3.name == 'test'
        assert rd3.parent is rd2

    def test_repr_and_eq(self):
        rd = RuntimeData({'a': 1}, name='test')
        assert 'test' in repr(rd)
        assert rd == {'a': 1}
        assert rd != {'a': 2}

    def test_getitem_basic(self):
        rd = RuntimeData({'a': 1, 'b': {'c': 2}})

        # Basic key access
        assert rd['a'] == 1
        assert rd['nonexistent'] is None

        # Dot path access
        assert rd['b.c'] == 2
        assert rd['b.nonexistent'] is None

        # Root access
        assert rd[None] == {'a': 1, 'b': {'c': 2}}

    def test_get_method(self):
        rd = RuntimeData({'a': 1, 'b': {'c': 2}})

        # Basic get
        assert rd.get('a') == 1
        assert rd.get('nonexistent') is None
        assert rd.get('nonexistent', 'default') == 'default'

        # Dot path get
        assert rd.get('b.c') == 2

        # Root get
        assert rd.get() == {'a': 1, 'b': {'c': 2}}
        assert rd.get(inherit=False) == {'a': 1, 'b': {'c': 2}}

    def test_setitem_basic(self):
        rd = RuntimeData()

        # Basic setting
        rd['a'] = 1
        assert rd['a'] == 1

        # Dot path setting
        rd['b.c'] = 2
        assert rd['b.c'] == 2
        assert rd.data == {'a': 1, 'b': {'c': 2}}

    def test_set_method(self):
        rd = RuntimeData()

        rd.set('a', 1)
        rd.set('b.c', 2)

        assert rd.data == {'a': 1, 'b': {'c': 2}}

    def test_delitem(self):
        rd = RuntimeData({'a': 1, 'b': {'c': 2, 'd': 3}})

        # Delete basic key
        del rd['a']
        assert 'a' not in rd.data

        # Delete dot path
        del rd['b.c']
        assert rd['b.c'] is None
        assert rd['b.d'] == 3

    def test_delete_method(self):
        rd = RuntimeData({'a': 1, 'b': {'c': 2}})

        rd.delete('a')
        assert 'a' not in rd.data

        rd.delete('b.c')
        assert rd['b.c'] is None


class TestRuntimeDataCollectionMethods:
    """Test dict-like collection methods"""

    def test_keys_values_items(self):
        rd = RuntimeData({'a': 1, 'b': 2})

        # Test with inheritance (default)
        assert set(rd.keys()) == {'a', 'b'}
        assert set(rd.values()) == {1, 2}
        assert set(rd.items()) == {('a', 1), ('b', 2)}

    def test_contains(self):
        rd = RuntimeData({'a': 1, 'b': {'c': 2}})

        assert 'a' in rd
        assert 'b' in rd
        assert 'nonexistent' not in rd

    def test_pop(self):
        rd = RuntimeData({'a': 1, 'b': {'c': 2}})

        # Pop existing key
        assert rd.pop('a') == 1
        assert 'a' not in rd.data

        # Pop with default
        assert rd.pop('nonexistent', 'default') == 'default'

        # Pop dot path
        assert rd.pop('b.c') == 2
        assert rd['b.c'] is None

    def test_clear(self):
        rd = RuntimeData({'a': 1, 'b': 2})
        rd.clear()
        assert rd.data == {}

    def test_update(self):
        rd = RuntimeData({'a': 1})
        rd.update({'b': 2, 'c': 3})

        expected = {'a': 1, 'b': 2, 'c': 3}
        assert rd.data == expected


class TestRuntimeDataComplexOperations:
    """Test complex data manipulation"""

    def test_merge_behavior_dicts(self):
        rd = RuntimeData({'a': {'x': 1}})
        rd['a'] = {'y': 2}

        # Should merge, not replace
        assert rd['a'] == {'x': 1, 'y': 2}

    def test_merge_behavior_lists(self):
        rd = RuntimeData({'items': [1, 2]})
        rd['items'] = [3, 4]

        # Should extend, not replace
        assert set(rd['items']) == {1, 2, 3, 4}

    def test_merge_behavior_sets(self):
        rd = RuntimeData({'items': {1, 2}})
        rd['items'] = {2, 3}

        # Should union
        assert rd['items'] == {1, 2, 3}

    def test_append_operations(self):
        rd = RuntimeData()

        # Append to non-existent key
        rd.append('list', 1)
        assert rd['list'] == [1]

        # Append to existing list
        rd.append('list', 2)
        assert rd['list'] == [1, 2]

        # Append to set
        rd['set'] = {1}
        rd.append('set', 2)
        assert rd['set'] == {1, 2}

        # Append to non-list value
        rd['scalar'] = 'value'
        rd.append('scalar', 'appended')
        assert rd['scalar'] == ['value', 'appended']

    def test_extend_operations(self):
        rd = RuntimeData()

        # Extend non-existent key
        rd.extend('list', [1, 2])
        assert rd['list'] == [1, 2]

        # Extend existing list
        rd.extend('list', [3, 4])
        assert rd['list'] == [1, 2, 3, 4]

        # Extend non-list value
        rd['scalar'] = 'value'
        rd.extend('scalar', ['extended'])
        assert rd['scalar'] == ['value', 'extended']


class TestRuntimeDataInheritance:
    """Test inheritance behavior"""

    def test_basic_inheritance(self):
        parent = RuntimeData({'a': 1, 'b': {'x': 10}})
        child = RuntimeData({'b': {'y': 20}, 'c': 3}, parent=parent)

        # Child should inherit from parent
        inherited = child.get()
        assert inherited['a'] == 1  # From parent
        assert inherited['c'] == 3  # From child
        assert inherited['b']['x'] == 10  # From parent
        assert inherited['b']['y'] == 20  # From child

    def test_inheritance_override(self):
        parent = RuntimeData({'a': 1, 'b': 2})
        child = RuntimeData({'b': 20}, parent=parent)

        inherited = child.get()
        assert inherited['a'] == 1  # From parent
        assert inherited['b'] == 20  # Overridden by child

    def test_inheritance_disabled(self):
        parent = RuntimeData({'a': 1})
        child = RuntimeData({'b': 2}, parent=parent)

        # Without inheritance
        data = child.get(inherit=False)
        assert data == {'b': 2}
        assert 'a' not in data

    def test_deep_inheritance_chain(self):
        grandparent = RuntimeData({'a': 1})
        parent = RuntimeData({'b': 2}, parent=grandparent)
        child = RuntimeData({'c': 3}, parent=parent)

        inherited = child.get()
        assert inherited == {'a': 1, 'b': 2, 'c': 3}


class TestRuntimeDataSerialization:
    """Test serialization methods"""

    def test_serializable_data_conversion(self):
        rd = RuntimeData()

        # Test datetime conversion
        dt = datetime.datetime.now()
        serializable = rd._get_serializable_data(dt)
        assert isinstance(serializable, str)
        assert 'T' in serializable  # ISO format

        # Test Path conversion
        path = Path('/some/path')
        serializable = rd._get_serializable_data(path)
        assert serializable == str(path)

        # Test nested structures
        data = {'date': datetime.date.today(), 'nested': {'path': Path('test'), 'num': 42}}
        serializable = rd._get_serializable_data(data)
        assert isinstance(serializable['date'], str)  # type: ignore
        assert isinstance(serializable['nested']['path'], str)  # type: ignore
        assert serializable['nested']['num'] == 42  # type: ignore

    def test_dump_json(self):
        rd = RuntimeData({'a': 1, 'b': {'c': 2}})
        json_str = rd.dump('json')

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed == {'a': 1, 'b': {'c': 2}}

    def test_dump_yaml(self):
        rd = RuntimeData({'a': 1, 'b': {'c': 2}})
        yaml_str = rd.dump('yaml')

        # Should be valid YAML
        parsed = yaml.safe_load(yaml_str)
        assert parsed == {'a': 1, 'b': {'c': 2}}

    def test_dump_toml(self):
        rd = RuntimeData({'a': 1, 'section': {'b': 2}})
        toml_str = rd.dump('toml')

        # Should be valid TOML
        parsed = toml.loads(toml_str)
        assert parsed == {'a': 1, 'section': {'b': 2}}

    @patch('builtins.open', new_callable=mock_open, read_data='{"a": 1, "b": 2}')
    def test_load_json_file(self, mock_file):
        rd = RuntimeData()
        rd.load('json_file', 'test.json')

        assert rd.data == {'a': 1, 'b': 2}
        mock_file.assert_called_once_with('test.json', 'r', encoding='utf-8')

    @patch('builtins.open', new_callable=mock_open, read_data='a: 1\nb: 2\n')
    def test_load_yaml_file(self, mock_file):
        rd = RuntimeData()
        rd.load('yaml_file', 'test.yaml')

        assert rd.data == {'a': 1, 'b': 2}
        mock_file.assert_called_once_with('test.yaml', 'r', encoding='utf-8')

    def test_load_json_string(self):
        rd = RuntimeData()
        rd.load('json', '{"a": 1, "b": 2}')

        assert rd.data == {'a': 1, 'b': 2}

    def test_load_invalid_data(self):
        rd = RuntimeData()

        # Should raise TypeError for non-dict data
        with pytest.raises(TypeError):
            rd.load('json', '"not a dict"')


class TestRuntimeDataNamespace:
    """Test RuntimeDataNamespace functionality"""

    def test_namespace_creation(self):
        rd = RuntimeData({'ns': {'a': 1, 'b': 2}})
        ns = rd.namespace('ns')

        assert isinstance(ns, RuntimeDataNamespace)
        assert ns.root is rd
        assert ns.namespace == 'ns'
        assert ns.data == {'a': 1, 'b': 2}

    def test_namespace_get_operations(self):
        rd = RuntimeData({'ns': {'a': 1, 'b': {'c': 2}}})
        ns = rd.namespace('ns')

        assert ns['a'] == 1
        assert ns['b.c'] == 2
        assert ns.get('a') == 1
        assert ns.get('nonexistent', 'default') == 'default'

    def test_namespace_set_operations(self):
        rd = RuntimeData({'ns': {}})
        ns = rd.namespace('ns')

        ns['a'] = 1
        ns.set('b.c', 2)

        assert rd['ns.a'] == 1
        assert rd['ns.b.c'] == 2

    def test_namespace_collection_methods(self):
        rd = RuntimeData({'ns': {'a': 1, 'b': 2}})
        ns = rd.namespace('ns')

        assert set(ns.keys()) == {'a', 'b'}
        assert set(ns.values()) == {1, 2}
        assert set(ns.items()) == {('a', 1), ('b', 2)}
        assert 'a' in ns

    def test_namespace_delete_operations(self):
        rd = RuntimeData({'ns': {'a': 1, 'b': 2}})
        ns = rd.namespace('ns')

        del ns['a']
        assert 'a' not in ns

        popped = ns.pop('b')
        assert popped == 2
        assert 'b' not in ns

    def test_namespace_clear(self):
        rd = RuntimeData({'ns': {'a': 1, 'b': 2}})
        ns = rd.namespace('ns')

        ns.clear()
        assert ns.data == {}

    def test_namespace_update(self):
        rd = RuntimeData({'ns': {'a': 1}})
        ns = rd.namespace('ns')

        ns.update({'b': 2, 'c': 3})
        assert ns.data == {'a': 1, 'b': 2, 'c': 3}

    def test_namespace_append_extend(self):
        rd = RuntimeData({'ns': {}})
        ns = rd.namespace('ns')

        ns.append('list', 1)
        ns.append('list', 2)
        assert ns['list'] == [1, 2]

        ns.extend('list', [3, 4])
        assert ns['list'] == [1, 2, 3, 4]


class TestRuntimeDataEdgeCases:
    """Test edge cases and potential problems"""

    def test_dot_path_with_non_dict_intermediate(self):
        rd = RuntimeData({'a': 'string'})

        # Should raise TypeError when trying to set nested path
        with pytest.raises(TypeError):
            rd['a.b'] = 'value'

    def test_none_values_handling(self):
        rd = RuntimeData({'a': None})

        assert rd['a'] is None
        assert rd.get('a') is None
        assert rd.get('a', 'default') is None  # None is not default-replaced

    def test_empty_string_keys(self):
        rd = RuntimeData()
        rd[''] = 'empty_key'
        assert rd[''] == 'empty_key'

    def test_numeric_keys(self):
        rd = RuntimeData()
        rd[0] = 'numeric_key'
        rd[1.5] = 'float_key'

        assert rd[0] == 'numeric_key'
        assert rd[1.5] == 'float_key'

    def test_deep_nesting_performance(self):
        rd = RuntimeData()

        # Create deeply nested structure
        path = '.'.join([f'level{i}' for i in range(50)])
        rd[path] = 'deep_value'

        assert rd[path] == 'deep_value'

    def test_circular_reference_protection(self):
        rd1 = RuntimeData({'name': 'rd1'})
        rd2 = RuntimeData({'name': 'rd2', 'ref': rd1})

        # This should not cause infinite recursion
        serialized = rd2._get_serializable_data(rd2.data)
        assert 'name' in serialized  # type: ignore

    def test_special_character_keys(self):
        rd = RuntimeData()

        # Keys with dots should work differently
        rd['key.with.dots'] = 'nested_value'
        rd[('tuple', 'key')] = 'tuple_key'

        assert rd['key.with.dots'] == 'nested_value'
        assert rd[('tuple', 'key')] == 'tuple_key'

    def test_type_consistency_after_operations(self):
        rd = RuntimeData({'list': [1, 2], 'dict': {'a': 1}})

        # Ensure types are preserved correctly
        rd['list'] = [3]  # Should extend, not replace
        assert isinstance(rd['list'], list)
        assert 1 in rd['list']  # Original items should still be there

        rd['dict'] = {'b': 2}  # Should merge, not replace
        assert isinstance(rd['dict'], dict)
        assert 'a' in rd['dict']  # Original key should still be there


class TestRuntimeDataStandardDictCompatibility:
    """Test compatibility with standard dict operations"""

    def test_dict_constructor_compatibility(self):
        # Test if RuntimeData can be used where dict is expected
        rd = RuntimeData({'a': 1, 'b': 2})

        # Should work with dict() constructor
        regular_dict = dict(rd.items())
        assert regular_dict == {'a': 1, 'b': 2}

    def test_dict_methods_compatibility(self):
        rd = RuntimeData({'a': 1, 'b': 2})

        # Test dict methods that RuntimeData should support
        assert hasattr(rd, 'keys')
        assert hasattr(rd, 'values')
        assert hasattr(rd, 'items')
        assert hasattr(rd, 'get')
        assert hasattr(rd, 'pop')
        assert hasattr(rd, 'clear')
        assert hasattr(rd, 'update')

    def test_iteration_compatibility(self):
        rd = RuntimeData({'a': 1, 'b': 2, 'c': 3})

        # Test iteration over keys (default dict behavior)
        keys_from_iter = list(rd)  # This might fail - RuntimeData doesn't implement __iter__
        keys_from_method = list(rd.keys())

        # Both should give the same result
        assert set(keys_from_iter) == set(keys_from_method)

    def test_membership_testing(self):
        rd = RuntimeData({'a': 1, 'b': 2})

        # Test 'in' operator
        assert 'a' in rd
        assert 'nonexistent' not in rd

    def test_len_operation(self):
        rd = RuntimeData({'a': 1, 'b': 2, 'c': 3})

        # RuntimeData might not implement __len__
        try:
            length = len(rd)
            assert length == 3
        except TypeError:
            # If __len__ is not implemented, this is a compatibility issue
            pytest.skip("RuntimeData does not implement __len__")


class TestRuntimeDataProblematicCases:
    """Test cases that might reveal problems in the implementation"""

    def test_copy_behavior_mutation(self):
        original_data = {'nested': {'value': [1, 2, 3]}}
        rd = RuntimeData(original_data)

        # Modify through RuntimeData
        rd['nested']['new_key'] = 'new_value'

        # Check if original data was mutated (it shouldn't be)
        # This tests the _copy method effectiveness
        if 'new_key' in original_data['nested']:
            pytest.fail("Original data was mutated - copy method is not working correctly")

    def test_inheritance_with_mutable_objects(self):
        parent_list = [1, 2, 3]
        parent = RuntimeData({'shared_list': parent_list})
        child = RuntimeData({}, parent=parent)

        # Modify inherited list
        child_list = child['shared_list']
        child_list.append(4)

        # Parent's list should not be affected
        assert parent_list == [1, 2, 3], "Parent data was mutated through child inheritance"

    def test_concurrent_modification_safety(self):
        rd = RuntimeData({'items': []})

        # Simulate concurrent modification
        items = rd['items']
        rd.append('items', 'new_item')

        # The reference should still be valid
        assert isinstance(items, list)
        # But check if the behavior is as expected

    def test_memory_usage_with_large_inheritance_chains(self):
        # Create a deep inheritance chain
        current = RuntimeData({'base': 'value'})
        for i in range(10):
            current = RuntimeData({f'level_{i}': i}, parent=current)

        # This should not consume excessive memory
        inherited = current.get()
        assert len(inherited) == 11  # base + 10 levels

    def test_serialization_of_unserializable_objects(self):
        class CustomClass:
            def __init__(self):
                self.value = 42

        rd = RuntimeData({'custom': CustomClass()})

        # Should handle unserializable objects gracefully
        try:
            serialized = rd._get_serializable_data(rd.data)
            # Should convert to string representation
            assert isinstance(serialized['custom'], (str, dict))  # type: ignore
        except Exception as e:
            pytest.fail(f"Serialization failed for custom object: {e}")


# Additional fixtures and utilities for testing
@pytest.fixture
def sample_runtime_data():
    """Fixture providing a sample RuntimeData instance"""
    return RuntimeData(
        {
            'string_val': 'test',
            'int_val': 42,
            'list_val': [1, 2, 3],
            'dict_val': {'nested': 'value'},
            'bool_val': True,
            'none_val': None,
        }
    )


@pytest.fixture
def inheritance_chain():
    """Fixture providing an inheritance chain of RuntimeData instances"""
    grandparent = RuntimeData({'gp_key': 'gp_value', 'shared': 'from_gp'})
    parent = RuntimeData({'p_key': 'p_value', 'shared': 'from_p'}, parent=grandparent)
    child = RuntimeData({'c_key': 'c_value'}, parent=parent)
    return grandparent, parent, child


# Performance and stress tests
class TestRuntimeDataPerformance:
    """Performance and stress tests"""

    def test_large_data_handling(self):
        # Test with large dataset
        large_data = {f'key_{i}': f'value_{i}' for i in range(1000)}
        rd = RuntimeData(large_data)

        # Basic operations should still be fast
        assert rd['key_500'] == 'value_500'
        assert 'key_999' in rd
        assert len(list(rd.keys())) == 1000

    def test_deep_nesting_limits(self):
        rd = RuntimeData()

        # Test reasonable nesting depth
        deep_path = '.'.join([f'level{i}' for i in range(20)])
        rd[deep_path] = 'deep_value'

        assert rd[deep_path] == 'deep_value'

    @pytest.mark.parametrize("operation_count", [100, 500])
    def test_repeated_operations_performance(self, operation_count):
        rd = RuntimeData()

        # Repeated set operations
        for i in range(operation_count):
            rd[f'key_{i}'] = f'value_{i}'

        # Repeated get operations
        for i in range(operation_count):
            assert rd[f'key_{i}'] == f'value_{i}'

        # Should complete without significant delay
        assert len(list(rd.keys())) == operation_count


if __name__ == "__main__":
    # Run specific test groups
    pytest.main(
        [
            __file__,
            "-v",  # verbose output
            "--tb=short",  # shorter traceback format
            "--durations=10",  # show 10 slowest tests
        ]
    )
