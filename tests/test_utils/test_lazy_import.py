import pytest

from agently.utils import LazyImport


def test_import_package():
    json5 = LazyImport.import_package("json5")
    assert json5.loads('{"test":"ok"}') == {"test": "ok"}  # type: ignore
    loads = LazyImport.from_import("json5", "loads")
    assert loads('{"test":"ok"}') == {"test": "ok"}  # type: ignore
    with pytest.raises(ImportError):
        LazyImport.import_package("unknown_package", auto_install=False)
    with pytest.raises(ModuleNotFoundError):
        loads = LazyImport.from_import("json5", "unknown_method", auto_install=False)


if __name__ == "__main__":
    agently_stage = LazyImport.import_package("agently-stage", auto_install=True)
