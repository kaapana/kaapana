import logging
import os
import time
from urllib.parse import urljoin

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.remote.remote_connection import RemoteConnection
from urllib3.exceptions import MaxRetryError

from .logger import get_logger

logger = get_logger(__name__, logging.DEBUG)


class BaseDriver:
    """
    The methods only work in child classes that also inherit from a webdriver subclass
    like webdriver.Remote or webdriver.Chrome
    """

    def start(self, url=None):
        if url:
            self.url = url
        else:
            self.url = os.environ["KAAPANA_URL"]
        logger.info(f"Kaapana URL: {self.url}")
        self.get(self.url)
        self.kaapana_tab = self.current_window_handle
        logger.info(f"Accessed {self.url}")

    def login(self, user="kaapana", password="admin"):
        """
        Login to the Kaapana via Keycloak

        Return:
            False: If element with id = 'input-error' found.
            True: If this element not found.
        """
        username_field = self.find_element(By.ID, "username")
        password_field = self.find_element(By.ID, "password")
        username_field.send_keys(user)
        password_field.send_keys(password)
        sign_in_button = self.find_element(By.ID, "kc-login")
        sign_in_button.click()
        try:
            self.find_element(By.ID, "input-error")
            logger.warning("Login failed with wrong credentials.")
            return False
        except NoSuchElementException:
            logger.info("Login succeeded.")
            return True

    def check_header(self, platform_name="Kaapana platform"):
        header = self.find_element(By.TAG_NAME, "HEADER")
        if header.get_attribute("innerText") == platform_name:
            return True
        else:
            return False

    def set_new_password(self, new_password="admin"):
        """
        Set a new password upon first login via Keycloak.
        """
        new_password_field = self.find_element(By.ID, "password-new")
        confirm_password_field = self.find_element(By.ID, "password-confirm")

        new_password_field.send_keys(new_password)
        confirm_password_field.send_keys(new_password, Keys.ENTER)

    def menu_bar(self):
        return self.find_element(By.CLASS_NAME, "v-list")

    def switch_tab(self):
        for window_handle in self.window_handles:
            if window_handle != self.kaapana_tab:
                self.switch_to.window(window_handle)
                break

    def close_additional_tabs(self):
        for window_handle in self.window_handles:
            if window_handle != self.kaapana_tab:
                self.switch_to.window(window_handle)
                self.close()

    def in_subdomain(self, subdomain):
        url_start_string = urljoin(self.url, subdomain)
        return self.current_url.startswith(url_start_string)


class KaapanaRemoteDriver(webdriver.Remote, BaseDriver):

    def __init__(self):
        options = self.init_options()
        capabilities = self.init_capabilities()

        logger.info("Initialize Remote driver")
        # self.driver=webdriver.Chrome(options=options)
        self.hostname = "http://selenium:4444/wd/hub"
        # hostname = 'http://localhost:4444/wd/hub'
        remote_connection = RemoteConnection(self.hostname, ignore_proxy=True)
        t = time.time()
        while abs(t - time.time()) < 60:
            try:
                super().__init__(
                    remote_connection,
                    options=options,
                    desired_capabilities=capabilities,
                )
                self.implicitly_wait(5)
                self.set_page_load_timeout(600)
                logger.info("Successfully initialized KaapanRemoteDriver")
                break
            except MaxRetryError as e:
                time.sleep(2)
                logger.info(f"Retry super.__init__ due to {str(e)}")

    @staticmethod
    def init_options():
        options = webdriver.ChromeOptions()
        options.add_argument("ignore-certificate-errors")
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return options

    @staticmethod
    def init_capabilities():
        capabilities = DesiredCapabilities.CHROME.copy()
        capabilities["acceptSslCerts"] = True

        HTTP_PROXY = os.environ.get("HTTP_PROXY")
        HTTPS_PROXY = os.environ.get("HTTPS_PROXY")

        print(HTTP_PROXY, HTTPS_PROXY)

        if HTTP_PROXY or HTTPS_PROXY:
            # Only set proxy if at least one is defined
            proxy_config = {}
            if HTTP_PROXY:
                proxy_config["httpProxy"] = HTTP_PROXY
            if HTTPS_PROXY:
                proxy_config["sslProxy"] = HTTPS_PROXY
            proxy_object = Proxy(raw=proxy_config)
            proxy_object.add_to_capabilities(capabilities)

        return capabilities


class KaapanaChromeDriver(webdriver.Chrome, BaseDriver):

    def __init__(self):
        options = self.init_options()
        # capabilities = self.init_capabilities()

        logger.info("Initialize Chrome driver")
        # self.driver=webdriver.Chrome(options=options)
        super().__init__(executable_path=os.environ["executable_path"], options=options)

        self.implicitly_wait(5)

    @staticmethod
    def init_options():
        options = webdriver.ChromeOptions()
        options.add_argument("ignore-certificate-errors")
        # options.add_argument('--headless')
        # options.add_argument('--no-sandbox')
        # options.add_argument('--disable-dev-shm-usage')
        return options

    @staticmethod
    def init_capabilities():
        capabilities = DesiredCapabilities.CHROME.copy()
        capabilities["acceptSslCerts"] = True

        HTTP_PROXY = os.environ.get("HTTP_PROXY")
        HTTPS_PROXY = os.environ.get("HTTPS_PROXY")

        print(HTTP_PROXY, HTTPS_PROXY)

        if HTTP_PROXY or HTTPS_PROXY:
            # Only set proxy if at least one is defined
            proxy_config = {}
            if HTTP_PROXY:
                proxy_config["httpProxy"] = HTTP_PROXY
            if HTTPS_PROXY:
                proxy_config["sslProxy"] = HTTPS_PROXY
            proxy_object = Proxy(raw=proxy_config)
            proxy_object.add_to_capabilities(capabilities)

        return capabilities
