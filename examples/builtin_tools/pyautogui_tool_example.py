import asyncio
import os

from agently.builtins.tools import PyAutoGUI

TARGET_URL = os.getenv("PYAUTOGUI_TARGET_URL", "https://github.com/AgentEra/Agently")
RUN_REAL = os.getenv("RUN_PYAUTOGUI", "1") == "1"
OPEN_MODE = os.getenv("PYAUTOGUI_OPEN_MODE", "hotkey").strip().lower()
if OPEN_MODE not in ("hotkey", "system"):
    OPEN_MODE = "hotkey"
BROWSER_APP = os.getenv("PYAUTOGUI_BROWSER_APP", "Google Chrome").strip() or None
ACTIVATE_BROWSER = os.getenv("PYAUTOGUI_ACTIVATE_BROWSER", "1" if OPEN_MODE == "hotkey" else "0") == "1"
ACTION = os.getenv("PYAUTOGUI_ACTION", "open_and_read").strip().lower()
if ACTION not in ("open", "read_active", "open_and_read"):
    ACTION = "open_and_read"

pyautogui_tool = PyAutoGUI(
    new_tab=True,
    wait_seconds=1.5,
    dry_run=not RUN_REAL,
    open_mode=OPEN_MODE,
    activate_browser=ACTIVATE_BROWSER,
    browser_app=BROWSER_APP,
)


async def main():
    print(
        "[PYAUTOGUI_CONFIG]",
        {
            "run_real": RUN_REAL,
            "open_mode": OPEN_MODE,
            "activate_browser": ACTIVATE_BROWSER,
            "browser_app": BROWSER_APP,
            "action": ACTION,
            "target_url": TARGET_URL,
        },
    )
    if ACTION == "open":
        result = await pyautogui_tool.open_url(TARGET_URL)
    elif ACTION == "read_active":
        result = await pyautogui_tool.read_active_tab()
    else:
        result = await pyautogui_tool.open_and_read_url(TARGET_URL)
    print("[PYAUTOGUI_OPEN_URL]")
    print(result)


asyncio.run(main())
