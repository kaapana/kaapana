import logging
import os
import shutil
import subprocess
import sys
from urllib.parse import urljoin

from kaapana_test.utils.logger import get_logger
from playwright.sync_api import sync_playwright
from selenium.webdriver.common.by import By

logger = get_logger(__name__, logging.DEBUG)


class ElementWrapper:
    def __init__(self, handle):
        self._h = handle

    def send_keys(self, text):
        # Prefer fill for input elements, use type for incremental typing
        try:
            self._h.fill(text)
        except Exception:
            self._h.type(text)

    def click(self):
        self._h.click()

    def get_attribute(self, name):
        if name in ("innerText", "textContent"):
            return self._h.inner_text()
        return self._h.get_attribute(name)


class KaapanaPlaywrightDriver:
    def __init__(self, headless=True):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=headless)
        # allow navigating to sites with self-signed or otherwise invalid certs
        self._context = self._browser.new_context(ignore_https_errors=True)
        self._page = self._context.new_page()
        self.kaapana_tab = self._page

    @property
    def current_window_handle(self):
        return self._page

    @property
    def current_url(self):
        return self._page.url

    def start(self, url=None):
        if url:
            self.url = url
        else:
            self.url = os.environ["KAAPANA_URL"]
        logger.info(f"Kaapana URL: {self.url}")
        self.get(self.url)
        self.kaapana_tab = self._page

    def get(self, url):
        self._page.goto(url)

    def refresh(self):
        self._page.reload()

    def close(self):
        # close current page
        try:
            self._page.close()
        except Exception:
            pass

    def login(self, user="kaapana", password="admin"):
        username = self.find_element(By.ID, "username")
        password_field = self.find_element(By.ID, "password")
        username.send_keys(user)
        password_field.send_keys(password)
        sign_in = self.find_element(By.ID, "kc-login")
        sign_in.click()
        try:
            self.find_element(By.ID, "input-error")
            logger.info("Login failed with incorrect credentials.")
            return False
        # There can be other problems logging in, but if the error element is not found, we assume login succeeded
        except Exception:
            logger.info("Login succeeded.")
            return True

    def set_new_password(self, new_password="admin"):
        new_password_field = self.find_element(By.ID, "password-new")
        confirm_password_field = self.find_element(By.ID, "password-confirm")
        new_password_field.send_keys(new_password)
        confirm_password_field.send_keys(new_password)
        # Press Enter if needed
        try:
            confirm_password_field._h.press("Enter")
        except Exception:
            try:
                # fallback: click a submit button if present
                btn = self._page.query_selector("button[type=submit]")
                if btn:
                    btn.click()
            except Exception:
                pass

    def menu_bar(self):
        return self.find_element(By.CLASS_NAME, "v-list")

    @property
    def switch_to(self):
        # mimic Selenium's switch_to property with window handling methods
        class Sw:
            def __init__(self, drv):
                self.drv = drv

            def window(self, handle):
                # handle is a Page instance
                try:
                    self.drv._page = handle
                    self.drv.kaapana_tab = handle
                except Exception:
                    pass

        return Sw(self)

    @property
    def window_handles(self):
        return self._context.pages

    def switch_tab(self):
        for pg in self._context.pages:
            if pg != self.kaapana_tab:
                self._page = pg
                self.kaapana_tab = pg
                break

    def close_additional_tabs(self):
        for pg in list(self._context.pages):
            if pg != self.kaapana_tab:
                pg.close()

    def in_subdomain(self, subdomain):
        url_start_string = urljoin(self.url, subdomain)
        return self._page.url.startswith(url_start_string)

    def implicitly_wait(self, secs):
        # set default timeout in ms
        self._page.set_default_timeout(int(secs * 1000))

    def find_element(self, by, value):
        if by == By.ID:
            sel = f"#{value}"
        elif by == By.CLASS_NAME:
            sel = f".{value}"
        elif by == By.TAG_NAME:
            sel = value
        else:
            sel = value
        handle = self._page.wait_for_selector(sel, timeout=5000)
        return ElementWrapper(handle)

    def quit(self):
        try:
            self._context.close()
            self._browser.close()
        finally:
            try:
                self._pw.stop()
            except Exception:
                pass


def ensure_playwright_installed() -> None:
    logger.info(
        "Running 'playwright install' to fetch browsers (output will be logged)"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "playwright", "install"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
        )
        out = proc.stdout.decode(errors="replace") if proc.stdout is not None else ""
        logger.info("'playwright install' finished successfully. Output:\n%s", out)
    except subprocess.CalledProcessError as e:
        out = e.stdout.decode(errors="replace") if getattr(e, "stdout", None) else ""
        logger.exception(
            "'playwright install' failed (rc=%s). Output:\n%s",
            getattr(e, "returncode", None),
            out,
        )
        raise

    logger.info("Running 'playwright install-deps' (output will be logged)")
    try:
        cmd = [sys.executable, "-m", "playwright", "install-deps"]
        # if not running as root, try to use sudo
        if os.geteuid() != 0:
            sudo_path = shutil.which("sudo")
            if sudo_path:
                cmd = [sudo_path] + cmd
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True
        )
        out = proc.stdout.decode(errors="replace") if proc.stdout is not None else ""
        logger.info("'playwright install-deps' finished successfully. Output:\n%s", out)
    except subprocess.CalledProcessError as e:
        out = e.stdout.decode(errors="replace") if getattr(e, "stdout", None) else ""
        logger.exception(
            "'playwright install-deps' failed (rc=%s). Output:\n%s",
            getattr(e, "returncode", None),
            out,
        )
        raise
