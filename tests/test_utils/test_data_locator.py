import pytest
from agently.utils.DataPathBuilder import DataPathBuilder
from agently.utils.DataLocator import DataLocator

sample_data = {
    "a": {"b": {"c": [1, 2, {"d": "target"}], "list": [100, 200]}},
    "x": [{"y": 123}, {"y": 456}],
}

sample_root_list = [
    {"id": "news-1", "can_use": True, "relevance_score": 95},
    {"id": "news-2", "can_use": False, "relevance_score": 70},
]


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


def test_root_list_dot_path_locate():
    assert DataLocator.locate_path_in_dict(sample_root_list, "[0].id", style="dot") == "news-1"
    assert DataLocator.locate_path_in_dict(sample_root_list, "[*].id", style="dot") == ["news-1", "news-2"]
    assert DataLocator.locate_path_in_dict(sample_root_list, "[*].can_use", style="dot") == [True, False]


def test_root_list_slash_path_locate():
    assert DataLocator.locate_path_in_dict(sample_root_list, "/0/id", style="slash") == "news-1"
    assert DataLocator.locate_path_in_dict(sample_root_list, "/[*]/id", style="slash") == ["news-1", "news-2"]
