from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import NoSuchElementException
from .helper import MainDriver
from .logger import get_logger
import logging
import time

logger = get_logger(__name__, logging.DEBUG)

###############################
### General
###############################


def first_login(user="kaapana", default_password="kaapana", new_password="admin"):
    """
    Login to kaapan the first time.
    1. Login using default credentials
    2. Set a new password
    """
    logger.info("Login the first time to Kaapana")
    if refresh_until_loadable(user=user, password=default_password):
        logger.info("Set new password")
        MainDriver.set_new_password(new_password)
        return True
    else:
        logger.warning(
            "Login with default credentials failed. Try login with new credentials."
        )
        MainDriver.refresh()
        return MainDriver.login(user, new_password)


def refresh_until_loadable(user="kaapana", password="admin"):
    """
    Refreshes the page, until the login form is found.
    Then does the login.
    """
    t = time.time()
    while abs(t - time.time()) < 60:
        try:
            return MainDriver.login(user, password)
        except NoSuchElementException as e:
            logger.warning("Refresh the page and retry login.")
            time.sleep(2)
            MainDriver.refresh()
    logger.error(f"Login failed because login field was not found")
    exit(1)


def switch_to_kaapana_tab():
    MainDriver.switch_to.window(MainDriver.kaapana_tab)


def close_all_additional_tabs():
    MainDriver.close_additional_tabs()
    switch_to_kaapana_tab()
