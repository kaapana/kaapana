# kaapana_playwright_driver_async.py
import logging

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


async def ensure_playwright_installed():
    import subprocess
    import sys

    logger.info("Installing Playwright browsers...")
    subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
    subprocess.run([sys.executable, "-m", "playwright", "install-deps"], check=True)


class KaapanaPlaywrightDriver:
    def __init__(self, headless=True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def start_driver(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(ignore_https_errors=True)
        self.page = await self.context.new_page()
        return self

    async def goto(self, url: str):
        await self.page.goto(url)

    async def login(self, user="kaapana", password="admin"):
        await self.page.fill("#username", user)
        await self.page.fill("#password", password)
        await self.page.click("#kc-login")
        # check if error element exists
        try:
            await self.page.wait_for_selector("#input-error", timeout=2000)
            logger.info("Login failed (wrong credentials)")
            return False
        except:
            logger.info("Login succeeded")
            return True

    async def set_new_password(self, new_password="admin"):
        await self.page.fill("#password-new", new_password)
        await self.page.fill("#password-confirm", new_password)
        try:
            await self.page.press("#password-confirm", "Enter")
        except:
            btn = await self.page.query_selector("button[type=submit]")
            if btn:
                await btn.click()

    async def quit(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
