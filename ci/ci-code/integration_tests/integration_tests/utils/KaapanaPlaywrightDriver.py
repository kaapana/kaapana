# kaapana_playwright_driver_async.py
import logging
from typing import Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

logger = logging.getLogger(__name__)


async def ensure_playwright_installed():
    import subprocess
    import sys

    logger.info("Installing Playwright browsers...")
    subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
    subprocess.run([sys.executable, "-m", "playwright", "install-deps"], check=True)


class KaapanaPlaywrightDriver:
    """
    Strongly typed Playwright driver so Pylance understands attributes.
    """

    playwright: Optional[Playwright]
    browser: Optional[Browser]
    context: Optional[BrowserContext]
    page: Optional[Page]

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def start_driver(self) -> "KaapanaPlaywrightDriver":
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(ignore_https_errors=True)
        self.page = await self.context.new_page()
        return self

    async def reset_session(self):
        if not self.context:
            raise RuntimeError("Driver not started. Call start_driver() first.")

        await self.context.clear_cookies()
        self.page = await self.context.new_page()

    async def goto(self, url: str):
        if not self.page:
            raise RuntimeError("Driver not started. Call start_driver() first.")

        await self.page.goto(url)

    async def login(self, user="kaapana", password="admin") -> bool:
        if not self.page:
            raise RuntimeError("Driver not started. Call start_driver() first.")

        await self.page.fill("#username", user)
        await self.page.fill("#password", password)
        await self.page.click("#kc-login")

        try:
            await self.page.wait_for_selector("#input-error", timeout=2000)
            logger.info("Login failed")
            return False
        except:
            logger.info("Login succeeded")
            return True

    async def set_new_password(self, new_password="admin"):
        if not self.page:
            raise RuntimeError("Driver not started. Call start_driver() first.")

        await self.page.fill("#password-new", new_password)
        await self.page.fill("#password-confirm", new_password)

        try:
            await self.page.press("#password-confirm", "Enter")
        except:
            btn = await self.page.query_selector("button[type=submit]")
            if btn:
                await btn.click()

    async def quit(self):
        # Close in correct order and only once
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self.context = None
        self.browser = None
        self.playwright = None
        self.page = None
