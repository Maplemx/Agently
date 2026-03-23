import logging
import pytest
import yaml
from agently import Agently


@pytest.mark.asyncio
async def test_settings():
    Agently.set_settings("test", "test")
    assert Agently.settings["test"] == "test"


def test_agently_set_api_key_and_alias_mapping():
    original_api_key = Agently.settings.get("agently.api_key", None)
    try:
        Agently.set_api_key("official-key")
        assert Agently.settings["agently.api_key"] == "official-key"

        Agently.set_settings("agently_api_key", "official-key-alias")
        assert Agently.settings["agently.api_key"] == "official-key-alias"
    finally:
        Agently.set_settings("agently.api_key", original_api_key)


def test_agently_load_settings_file(tmp_path, monkeypatch):
    config_path = tmp_path / "settings.yaml"
    env_path = tmp_path / ".env"

    config_path.write_text(
        yaml.safe_dump(
            {
                "test_main_package": {
                    "base_url": "${ENV.TEST_MAIN_PACKAGE_BASE_URL}",
                }
            }
        ),
        encoding="utf-8",
    )
    env_path.write_text("TEST_MAIN_PACKAGE_BASE_URL=https://example.com\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TEST_MAIN_PACKAGE_BASE_URL", raising=False)

    Agently.load_settings("yaml_file", str(config_path), auto_load_env=True)

    assert Agently.settings["test_main_package.base_url"] == "https://example.com"


def test_agently_load_settings_refresh_httpx_log_level(tmp_path):
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "runtime": {
                    "httpx_log_level": "INFO",
                }
            }
        ),
        encoding="utf-8",
    )

    Agently.load_settings("yaml_file", str(config_path))

    assert logging.getLogger("httpx").level == logging.INFO
    assert logging.getLogger("httpcore").level == logging.INFO
