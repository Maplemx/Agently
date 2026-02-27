import os
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from agently import Agently
from agently.builtins.tools import Playwright

ISSUES_URL = "https://github.com/AgentEra/Agently/issues?q=is%3Aissue%20state%3Aopen"


def configure_model():
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("DEEPSEEK_DEFAULT_MODEL", "gpt-4o-mini")
    auth = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not auth:
        raise RuntimeError(
            "Missing API key. Please set DEEPSEEK_API_KEY (or OPENAI_API_KEY) in your environment."
        )

    Agently.set_settings(
        "OpenAICompatible",
        {
            "base_url": base_url,
            "model": model,
            "model_type": "chat",
            "auth": auth,
        },
    )


def with_page(url: str, page: int) -> str:
    parsed = urlparse(url)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    query = dict(query_pairs)
    query["page"] = str(page)
    new_query = urlencode(query, doseq=True)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )


def analyze_one_page(agent, page_url: str, page: int):
    response = (
        agent.input(
            {
                "target_repo": "AgentEra/Agently",
                "issues_url": page_url,
                "page": page,
            }
        )
        .instruct(
            """
            You MUST use the available tool to open {issues_url} first.
            Extract issues from this page only.
            Prefer real issue URL if present; otherwise return empty string.
            If no issue is listed on this page, return an empty list.
            """
        )
        .output(
            {
                "page": (int, "Current page number"),
                "issues": [
                    {
                        "title": (str, "Issue title"),
                        "url": (str, "Issue URL"),
                        "risk_hint": (str, "A short risk hint"),
                    }
                ],
                "has_next_page_guess": (bool, "Whether another issues page likely exists"),
                "note": (str, "Short note for this page"),
            }
        )
        .get_response()
    )
    result = response.result.get_data()
    extra = response.result.full_result_data.get("extra", {})
    return result, extra.get("tool_logs", [])


def summarize_all(agent, page_results: list[dict], issues: list[dict]):
    agent.use_tools([])
    response = (
        agent.input(
            {
                "target_repo": "AgentEra/Agently",
                "page_results": page_results,
                "issues": issues,
            }
        )
        .instruct(
            """
            Summarize the paged issue scan result.
            Focus on risk level and actionable follow-ups.
            """
        )
        .output(
            {
                "repo": (str, "Repository"),
                "total_pages_checked": (int, "How many pages were checked"),
                "total_unique_issues": (int, "How many unique issues were found"),
                "summary": (str, "3-6 sentence summary"),
                "high_priority_count_estimate": (int, "Estimated number of high-priority issues"),
                "issues": [
                    {
                        "title": (str, "Issue title"),
                        "url": (str, "Issue URL"),
                        "risk_level": (str, "low / medium / high"),
                        "why_it_matters": (str, "Why this matters"),
                    }
                ],
                "next_actions": [(str, "Concrete action item")],
            }
        )
        .get_response()
    )
    return response.result.get_data()


def main():
    configure_model()
    agent = Agently.create_agent("issue-checker-loop")
    max_pages = int(os.getenv("ISSUE_SCAN_MAX_PAGES", "3"))
    playwright = Playwright(headless=True, timeout=45000)

    async def open_issues_page(url: str) -> dict:
        """
        Open GitHub issues page and return rendered content.
        """
        return await playwright.open(
            url=url,
            wait_until="domcontentloaded",
            max_text_length=12000,
        )

    agent.use_tools(open_issues_page)

    page_results: list[dict] = []
    all_tool_logs: list[dict] = []
    all_issues: list[dict] = []
    seen_keys: set[str] = set()

    for page in range(1, max_pages + 1):
        page_url = with_page(ISSUES_URL, page)
        page_result, tool_logs = analyze_one_page(agent, page_url, page)
        page_results.append(
            {
                "page": page,
                "url": page_url,
                "result": page_result,
            }
        )
        all_tool_logs.extend(tool_logs)

        issues = page_result.get("issues", []) if isinstance(page_result, dict) else []
        new_count = 0
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            title = str(issue.get("title", "")).strip()
            url = str(issue.get("url", "")).strip()
            key = url or title
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            all_issues.append(
                {
                    "title": title,
                    "url": url,
                    "risk_hint": str(issue.get("risk_hint", "")).strip(),
                    "page": page,
                }
            )
            new_count += 1

        print(f"[PAGE {page}] url={page_url} issues={len(issues)} new={new_count}")

        has_next = page_result.get("has_next_page_guess", False) if isinstance(page_result, dict) else False
        if not has_next:
            print(f"[STOP] model judged no next page at page {page}.")
            break
        if new_count == 0:
            print(f"[STOP] no new issues found at page {page}.")
            break

    final_report = summarize_all(agent, page_results, all_issues)

    print("[ISSUE_CHECK_RESULT]")
    print(final_report)
    print("[TOOL_LOGS]")
    print(all_tool_logs)


if __name__ == "__main__":
    main()
