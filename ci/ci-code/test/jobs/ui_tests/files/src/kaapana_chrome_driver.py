from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from urllib.parse import urljoin
from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.common.keys import Keys
import time
import os
from .logger import get_logger
import logging
from urllib3.exceptions import MaxRetryError
from selenium.common.exceptions import NoSuchElementException, TimeoutException

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

    def open_meta_dashboard_url(self):
        # meta_dashboard_url = urljoin(self.url, "#/web/meta/kibana0")
        meta_dashboard_url = urljoin(self.url, "#/web/meta/osdashboard0")
        self.get(meta_dashboard_url)

    def open_minio_url(self):
        meta_dashboard_url = urljoin(self.url, "#/web/store/minio")
        self.get(meta_dashboard_url)

    def open_airflow_url(self):
        meta_dashboard_url = urljoin(self.url, "#/web/flow/airflow")
        self.get(meta_dashboard_url)

    def open_segmentations_url(self):
        # segmentations = urljoin(self.url, "#/web/meta/kibana1")
        segmentations = urljoin(self.url, "#/web/meta/osdashboard1")
        self.get(segmentations)

    def open_extensions_url(self):
        extensions = urljoin(self.url, "#/extensions")
        self.get(extensions)

    def open_pending_applications_url(self):
        pending_applications = urljoin(self.url, "#/pending-applications")
        self.get(pending_applications)

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
        HTTP_PROXY = os.environ["HTTP_PROXY"]
        HTTPS_PROXY = os.environ["HTTPS_PROXY"]
        # Use the selenium Proxy object to add proxy capabilities
        proxy_config = {"httpProxy": HTTP_PROXY, "sslProxy": HTTPS_PROXY}
        proxy_object = Proxy(raw=proxy_config)
        capabilities = DesiredCapabilities.CHROME.copy()
        capabilities["acceptSslCerts"] = True
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
        HTTP_PROXY = os.environ["HTTP_PROXY"]
        HTTPS_PROXY = os.environ["HTTPS_PROXY"]
        # Use the selenium Proxy object to add proxy capabilities
        proxy_config = {"httpProxy": HTTP_PROXY, "sslProxy": HTTPS_PROXY}
        proxy_object = Proxy(raw=proxy_config)
        capabilities = DesiredCapabilities.CHROME.copy()
        capabilities["acceptSslCerts"] = True
        proxy_object.add_to_capabilities(capabilities)
        return capabilities
