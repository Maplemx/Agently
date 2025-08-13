import pytest
from agently.utils.DataPathBuilder import DataPathBuilder
from agently.utils.DataLocator import DataLocator

sample_data = {
    "a": {"b": {"c": [1, 2, {"d": "target"}], "list": [100, 200]}},
    "x": [{"y": 123}, {"y": 456}],
}


@pytest.mark.parametrize(
    "keys,value",
    [
        (["a", "b", "c", 2, "d"], "target"),
        (["a", "b", "list", 1], 200),
        (["x", 0, "y"], 123),
    ],
)
def test_dot_path_build_and_locate(keys, value):
    path = DataPathBuilder.build_dot_path(keys)
    result = DataLocator.locate_path_in_dict(sample_data, path, style="dot")
    assert result == value


@pytest.mark.parametrize(
    "keys,value",
    [
        (["a", "b", "c", 2, "d"], "target"),
        (["a", "b", "list", 1], 200),
        (["x", 1, "y"], 456),
    ],
)
def test_slash_path_build_and_locate(keys, value):
    path = DataPathBuilder.build_slash_path(keys)
    result = DataLocator.locate_path_in_dict(sample_data, path, style="slash")
    assert result == value


def test_empty_keys():
    assert DataPathBuilder.build_dot_path([]) == ""
    assert DataPathBuilder.build_slash_path([]) == ""
    assert DataLocator.locate_path_in_dict(sample_data, "", style="dot") == sample_data
    assert DataLocator.locate_path_in_dict(sample_data, "", style="slash") == sample_data
