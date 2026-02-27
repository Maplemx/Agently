import asyncio
import os

from agently.builtins.tools import Playwright

TARGET_URL = os.getenv("PLAYWRIGHT_TARGET_URL", "https://github.com/AgentEra/Agently")
SCREENSHOT_PATH = os.getenv("PLAYWRIGHT_SCREENSHOT_PATH")

playwright_tool = Playwright(
    headless=True,
    response_mode="markdown",
    max_content_length=8000,
    include_links=False,
    screenshot_path=SCREENSHOT_PATH,
)


async def main():
    result = await playwright_tool.open(url=TARGET_URL)
    print("[PLAYWRIGHT_OPEN]")
    print(result)


asyncio.run(main())
