import asyncio
import os

from agently.builtins.tools import Playwright, PyAutoGUI

GITHUB_URL = "https://github.com/AgentEra/Agently"

playwright = Playwright(headless=True)
pyautogui = PyAutoGUI()


async def main():
    playwright_result = await playwright.open(
        url=GITHUB_URL,
        wait_until="domcontentloaded",
        screenshot_path="examples/output/playwright_github.png",
    )
    print("[PLAYWRIGHT_OPEN]")
    print(playwright_result)

    run_real_pyautogui = os.getenv("RUN_PYAUTOGUI", "0") == "1"
    pyautogui_result = await pyautogui.open_url(
        url=GITHUB_URL,
        new_tab=True,
        wait_seconds=1.5,
        dry_run=not run_real_pyautogui,
    )
    print("[PYAUTOGUI_OPEN_URL]")
    print(pyautogui_result)


asyncio.run(main())
