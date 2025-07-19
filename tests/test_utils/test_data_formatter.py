import pytest

from agently.utils import DataFormatter


def test_sanitize():
    from pydantic import BaseModel, Field

    class MySubModel(BaseModel):
        "My Sub Model"

        dictionary: dict = Field(..., description="A Dictionary")
        some_list: list = Field(..., description="A List")

    class MyModel(BaseModel):
        "My Data Model"

        first: str = Field(..., description="Some String")
        second: int = Field(..., description="Some Integer")
        dict_list: list[dict[str, str]] = Field(..., description="A list of string dict")
        sub: MySubModel

    test_output = {
        "thinking": ([(str,)], "how to answer"),
        "reply": (str, "my reply"),
        "additional": MyModel,
    }
    assert DataFormatter.sanitize(test_output) == {
        "thinking": ([("str",)], "how to answer"),
        "reply": ("str", "my reply"),
        "additional": {
            "first": ("str", "Some String"),
            "second": ("int", "Some Integer"),
            "dict_list": ("list[dict[str, str]]", "A list of string dict"),
            "sub": (
                {
                    "dictionary": ("dict", "A Dictionary"),
                    "some_list": ("list", "A List"),
                },
            ),
        },
    }
    assert DataFormatter.sanitize(test_output, remain_type=True) == {
        "thinking": ([(str,)], "how to answer"),
        "reply": (str, "my reply"),
        "additional": {
            "first": (str, "Some String"),
            "second": (int, "Some Integer"),
            "dict_list": (list[dict[str, str]], "A list of string dict"),
            "sub": (
                {
                    "dictionary": (dict, "A Dictionary"),
                    "some_list": (list, "A List"),
                },
            ),
        },
    }


def test_to_str_dict():
    test_value = {
        1: str,
        2: 3,
    }
    assert DataFormatter.to_str_key_dict(test_value) == {"1": str, "2": 3}
    assert DataFormatter.to_str_key_dict(
        test_value,
        value_format="serializable",
    ) == {
        "1": "str",
        "2": 3,
    }
    assert DataFormatter.to_str_key_dict(
        test_value,
        value_format="str",
    ) == {
        "1": "str",
        "2": "3",
    }
