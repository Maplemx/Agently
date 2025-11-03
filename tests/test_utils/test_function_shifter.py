import pytest
from agently.utils import FunctionShifter


def test_kwargs():
    def test_func(*, a: str, b: int):
        return int(a) + b

    options = {
        "a": "1",
        "b": 2,
        "c": 3,
    }

    with pytest.raises(Exception):
        test_func(**options)

    new_test_func = FunctionShifter.auto_options_func(test_func)
    assert new_test_func(**options) == 3
