import pytest
import json
import yaml
import toml
from typing import cast
from agently.utils import RuntimeData


class TestRuntimeData:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.GLOBAL = object()
        self.grand_parent = RuntimeData(
            {"grand_parent": {"test": "OK"}, self.GLOBAL: {"g": 1, "p": {"a": 1}}},
            name="grand_parent",
        )
        self.parent = RuntimeData(
            {
                "parent": {"test": "OK"},
                self.GLOBAL: {
                    "g": 2,
                    "p": {
                        "b": 2,
                    },
                },
            },
            parent=self.grand_parent,
            name="parent",
        )
        self.data = RuntimeData(
            {
                "data": {"test": "OK"},
                self.GLOBAL: {
                    "g": 3,
                    "p": {
                        "c": 3,
                    },
                },
            },
            parent=self.parent,
            name="data",
        )

    def test_getting(self):
        assert self.data == {
            "grand_parent": {"test": "OK"},
            "parent": {"test": "OK"},
            "data": {"test": "OK"},
            self.GLOBAL: {
                "g": 3,
                "p": {
                    "a": 1,
                    "b": 2,
                    "c": 3,
                },
            },
        }
        # Inherit
        assert self.data["grand_parent"] == {"test": "OK"}
        assert self.data["parent.test"] == "OK"
        # Non-String Key Support
        assert RuntimeData(self.data[self.GLOBAL])["p.a"] == 1
        # Get Original Data without Inherit
        assert self.data.get(inherit=False) == {
            "data": {"test": "OK"},
            self.GLOBAL: {
                "g": 3,
                "p": {
                    "c": 3,
                },
            },
        }

    def test_setting_in_different_types(self):
        # Str
        self.grand_parent["update.test_str"] = ["Error", "No Pass"]
        self.parent["update.test_str"] = "Pass"
        assert self.data["update.test_str"] == "Pass"
        # List
        self.data["update.test_list"] = []
        self.parent["update.test_list"] = 1
        self.grand_parent["update.test_list"] = [2, 3]
        assert self.data["update.test_list"] == [1, 2, 3]
        # Int
        self.data["update.test_int"] = 1
        self.parent["update.test_int"] = [2, 3]
        self.grand_parent["update.test_int"] = [3, 4]
        assert self.data["update.test_int"] == 1
        # Set
        self.data["update.test_set"] = set()
        self.parent["update.test_set"] = [1, 2]
        self.grand_parent["update.test_set"] = (2, 3)
        assert self.data["update.test_set"] == {1, 2, 3}
        # Tuple
        self.data["update.test_tuple"] = 1
        self.parent["update.test_tuple"] = [1, 2]
        self.grand_parent["update.test_tuple"] = {2, 3}
        assert self.data["update.test_tuple"] == (1)
        # Dict
        self.data["update.test_dict"] = {
            "data": "OK",
            "global": {"g": 1, "p": {"a": 1}},
        }
        self.parent["update.test_dict"] = {
            "parent": "OK",
            "global": {"g": 2, "p": {"b": 2}},
        }
        self.grand_parent["update.test_dict"] = {
            "grand_parent": "OK",
            "global": {"g": 3, "p": {"c": 3}},
        }
        assert self.data["update.test_dict"] == {
            "data": "OK",
            "parent": "OK",
            "grand_parent": "OK",
            "global": {"g": 1, "p": {"a": 1, "b": 2, "c": 3}},
        }
        # RuntimeData.data Read Only
        with pytest.raises(AttributeError):
            self.data.data = {"new": "value"}  # type: ignore

    def test_del(self):
        self.data["delete_testing"] = {"to_delete": True, "to_keep": True}
        del self.data["delete_testing.to_delete"]
        assert self.data["delete_testing"] == {"to_keep": True}

    def test_namespace(self):
        data = RuntimeData(
            {
                "test": {
                    "result": "OK",
                },
                "others": {
                    "hello": "world",
                },
            }
        )
        namespace = data.namespace("test")
        assert namespace == {"result": "OK"}
        namespace.update({"updated": True})
        assert data["test"] == {
            "result": "OK",
            "updated": True,
        }
        namespace.set("updated_dict", {"test_1": {}})
        assert data["test"] == {
            "result": "OK",
            "updated": True,
            "updated_dict": {"test_1": {}},
        }
        namespace.update({"updated_dict.test_1": {"test": True}})
        assert data["test"] == {
            "result": "OK",
            "updated": True,
            "updated_dict": {"test_1": {"test": True}},
        }
        del namespace["updated_dict"]
        assert data["test"] == {
            "result": "OK",
            "updated": True,
        }

    def test_not_exists_namespace(self):
        data = RuntimeData(
            {
                "test": {
                    "result": "OK",
                },
                "others": {
                    "hello": "world",
                },
            }
        )
        not_exists_namespace = data.namespace("not_exists")
        assert data["not_exists"] is None
        assert data["not_exists.test"] is None
        assert not_exists_namespace.get("test") is None
        not_exists_namespace["test"] = "hello world"
        assert not_exists_namespace.get("test") == "hello world"
        assert data["not_exists.test"] == "hello world"

    def test_deep_inheritance(self):
        level3 = RuntimeData({"level": 3, "data": {"deep": "level3"}}, name="level3")
        level2 = RuntimeData({"level": 2, "data": {"deep": "level2"}}, parent=level3, name="level2")
        level1 = RuntimeData({"level": 1, "data": {"deep": "level1"}}, parent=level2, name="level1")

        assert level1["data.deep"] == "level1"
        assert level1["level"] == 1
        assert "level" in level1.keys()

    def test_special_objects(self):
        class CustomObj:
            def __init__(self, value):
                self.value = value

        obj = CustomObj(123)
        data = RuntimeData({"custom": obj, "none": None, "bool": True})

        assert data["custom"].value == 123
        assert data["none"] is None
        assert data["bool"] is True

    def test_error_handling(self):
        data = RuntimeData({"test": "value"})

        # Non-existed Key
        assert data.get("non_exist") is None
        assert data.get("non_exist", default="default") == "default"

        # Invalid Path
        with pytest.raises(TypeError):
            data["test.invalid.path"] = "value"

        # Del Non-existed Key will raise nothing
        del data["non_exist"]

    def test_advanced_namespace(self):
        data = RuntimeData({"ns1": {"a": 1, "b": {"deep": "value"}}, "ns2": {"x": [1, 2, 3]}})

        ns1 = data.namespace("ns1")
        ns2 = data.namespace("ns2")

        assert ns1["b.deep"] == "value"

        child_data = RuntimeData({"ns1": {"new": "child", "b": True}}, parent=data)
        child_ns1 = child_data.namespace("ns1")
        assert child_ns1["a"] == 1
        assert child_ns1["new"] == "child"
        assert child_ns1["b"] == True
        assert "b" in child_data["ns1"]

        del child_ns1["b"]
        assert child_data["ns1"]["b"] == {"deep": "value"}
        assert "b" in data["ns1"]

        del ns1["b"]
        assert "b" not in data["ns1"]

    def test_complex_merge(self):
        parent = RuntimeData(
            {
                "complex": {
                    "list": [1, 2],
                    "set": {3, 4},
                    "dict": {"a": 1, "b": {"nested": "value"}},
                    "tuple": (5, 6),
                }
            }
        )

        child = RuntimeData(
            {
                "complex": {
                    "list": [7],
                    "set": {8},
                    "dict": {"c": 2, "b": {"new": "data"}},
                    "tuple": (9,),
                }
            },
            parent=parent,
        )

        assert set(child["complex.list"]) == {1, 2, 7}
        assert child["complex.set"] == {3, 4, 8}
        assert child["complex.dict"]["b"] == {"nested": "value", "new": "data"}
        assert child["complex.tuple"] == (9,)

    def test_copy_behavior(self):
        data = RuntimeData({"a": {"b": 1}})
        # Result is a copy not a ref
        result = data["a"]
        result["b"] = 2
        assert data["a.b"] == 1
        assert result == {"b": 2}

    def test_project_practices(self):
        settings = RuntimeData()
        request_settings = settings.namespace("Request")
        request_settings["Test"] = True
        assert settings == {"Request": {"Test": True}}
        assert request_settings == {"Test": True}

        prompts = RuntimeData()
        prompts["INPUT"] = "Hello"
        assert prompts == {"INPUT": "Hello"}

    def test_load_data(self, tmp_path):
        # Temporary File Paths
        json_file = tmp_path / "test.json"
        yaml_file = tmp_path / "test.yaml"
        toml_file = tmp_path / "test.toml"

        # Testing Data
        json_data = '{"name": "json_test", "nested": {"value": 123}}'
        yaml_data = """
    name: yaml_test
    nested:
      value: 456
    """
        toml_data = """
    name = "toml_test"
    [nested]
    value = 789
    """

        # Write into Temporary Files
        json_file.write_text(json_data)
        yaml_file.write_text(yaml_data)
        toml_file.write_text(toml_data)

        # Load from string
        data1 = RuntimeData()
        data1.load("json", json_data)
        assert data1["name"] == "json_test"
        assert data1["nested.value"] == 123

        data2 = RuntimeData()
        data2.load("yaml", yaml_data)
        assert data2["name"] == "yaml_test"
        assert data2["nested.value"] == 456

        data3 = RuntimeData()
        data3.load("toml", toml_data)
        assert data3["name"] == "toml_test"
        assert data3["nested.value"] == 789

        # Load from file
        data4 = RuntimeData()
        data4.load("json_file", str(json_file))
        assert data4["name"] == "json_test"
        assert data4["nested.value"] == 123

        data5 = RuntimeData()
        data5.load("yaml_file", str(yaml_file))
        assert data5["name"] == "yaml_test"
        assert data5["nested.value"] == 456

        data6 = RuntimeData()
        data6.load("toml_file", str(toml_file))
        assert data6["name"] == "toml_test"
        assert data6["nested.value"] == 789

        # Exceptions
        data7 = RuntimeData()
        with pytest.raises(ValueError):
            data7.load("json", "invalid json data")

        with pytest.raises(TypeError):
            data7.load("unknown_type", json_data)  # type: ignore

    def test_dump_data(self):
        import datetime
        from pathlib import Path

        # Prepare test data with various serializable data types
        data = RuntimeData(
            {
                # Basic types
                "string": "hello",
                "number": 123,
                "float": 3.14,
                "boolean": True,
                "null": None,
                "list": [1, 2, 3],
                # Nested structures
                "nested": {"a": 1, "b": [2, 3], "c": {"d": 4}},
                # Special objects
                "datetime": datetime.datetime(2023, 1, 1, 12, 0),
                "date": datetime.date(2023, 1, 1),
                "path": Path("/tmp/test.txt"),
                # Container types
                "set": {1, 2, 3},
                "tuple": (4, 5, 6),
                # Nested RuntimeData
                "runtime_data": RuntimeData({"nested": "value"}),
            }
        )

        # Test JSON serialization
        json_result = data.dump("json")
        assert isinstance(json_result, str)
        loaded_json = cast(dict, json.loads(json_result))

        # Validate basic types
        assert loaded_json["string"] == "hello"
        assert loaded_json["number"] == 123
        assert loaded_json["float"] == 3.14
        assert loaded_json["boolean"] is True
        assert loaded_json["null"] is None
        assert loaded_json["list"] == [1, 2, 3]

        # Validate nested structures
        nested = loaded_json["nested"]
        assert nested["a"] == 1
        assert nested["b"] == [2, 3]
        assert nested["c"]["d"] == 4

        # Validate special object serialization
        assert loaded_json["datetime"] == "2023-01-01T12:00:00"
        assert loaded_json["date"] == "2023-01-01"
        assert loaded_json["path"] == "/tmp/test.txt"

        # Validate container types
        assert isinstance(loaded_json["set"], list)
        assert set(loaded_json["set"]) == {1, 2, 3}
        assert loaded_json["tuple"] == [4, 5, 6]

        # Validate nested RuntimeData
        assert loaded_json["runtime_data"] == {"nested": "value"}

        # Test YAML serialization
        yaml_result = data.dump("yaml")
        assert isinstance(yaml_result, str)
        loaded_yaml = yaml.safe_load(yaml_result)

        # Validate YAML serialization results
        assert loaded_yaml["number"] == 123
        assert loaded_yaml["nested"]["b"] == [2, 3]
        assert loaded_yaml["datetime"] == "2023-01-01T12:00:00"

        # Test TOML serialization
        toml_result = data.dump("toml")
        assert isinstance(toml_result, str)
        loaded_toml = toml.loads(toml_result)

        # Validate TOML serialization results
        assert loaded_toml["boolean"] is True
        assert loaded_toml["nested"]["a"] == 1
        assert loaded_toml["datetime"] == "2023-01-01T12:00:00"

        # Test handling of non-serializable objects
        class CustomClass:
            pass

        data_with_unserializable = RuntimeData(
            {
                "normal": "data",
                "custom_obj": CustomClass(),
                "function": lambda x: x,
                "nested": {"normal": 123, "custom_obj": CustomClass()},
            }
        )

        # Validate serialization results
        json_result = data_with_unserializable.dump("json")
        loaded_data = cast(dict, json.loads(json_result))
        # Verify serializable data is preserved
        assert loaded_data["normal"] == "data"
        assert loaded_data["nested"]["normal"] == 123

        # Verify non-serializable data is converted to strings
        assert isinstance(loaded_data["custom_obj"], str)
        assert isinstance(loaded_data["function"], str)
        assert isinstance(loaded_data["nested"]["custom_obj"], str)


def test_set_with_dot_path():
    runtime_data = RuntimeData()
    runtime_data.set("prompt.system.your_role", "Your Character")
    assert runtime_data["prompt"]["system"]["your_role"] == "Your Character"
