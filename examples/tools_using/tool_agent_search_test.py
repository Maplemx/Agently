import os

from dotenv import find_dotenv, load_dotenv

from agently import Agently
from agently.builtins.tools import Browse, Search


def _configure_model() -> None:
    load_dotenv(find_dotenv())
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_api_key:
        Agently.set_settings(
            "OpenAICompatible",
            {
                "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                "model": os.getenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat"),
                "model_type": "chat",
                "auth": deepseek_api_key,
            },
        )
        return

    Agently.set_settings(
        "OpenAICompatible",
        {
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"),
            "model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            "model_type": "chat",
            "auth": None,
        },
    )


def _validate_search_browse_chain(tool_logs: list[dict]) -> dict:
    names = [str(log.get("tool_name", "")).strip() for log in tool_logs]
    first_search = next((idx for idx, name in enumerate(names) if name.startswith("search")), -1)
    first_browse = next((idx for idx, name in enumerate(names) if name == "browse"), -1)
    return {
        "tool_names": names,
        "has_search": first_search >= 0,
        "has_browse": first_browse >= 0,
        "search_then_browse": first_search >= 0 and first_browse >= 0 and first_search < first_browse,
    }


def main():
    _configure_model()
    Agently.set_settings("tool.loop.enabled", True)
    Agently.set_settings("tool.loop.max_rounds", 4)
    Agently.set_settings("tool.loop.concurrency", 2)
    Agently.set_settings("tool.loop.timeout", 60)
    Agently.set_settings("runtime.show_tool_logs", True)

    agent = Agently.create_agent()
    search = Search(
        proxy=os.getenv("SEARCH_PROXY"),
        region="us-en",
        backend="auto",
    )
    browse = Browse(proxy=os.getenv("BROWSE_PROXY"))

    agent.use_tools([search.search, search.search_news, browse.browse])

    response = (
        agent.input("How to use Agently TriggerFlow")
        .instruct(
            [
                "Must with content that you actually browsed.",
            ]
        )
        .get_response()
    )
    result = response.result.get_data()
    extra = response.result.full_result_data.get("extra", {})
    tool_logs = extra.get("tool_logs", []) if isinstance(extra, dict) else []

    print("[RESULT]")
    print(result)
    print("\n[TOOL_LOG_COUNT]")
    print(len(tool_logs))
    print("\n[TOOL_CHAIN_VALIDATION]")
    print(_validate_search_browse_chain(tool_logs if isinstance(tool_logs, list) else []))


if __name__ == "__main__":
    main()
