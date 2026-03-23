#!/usr/bin/env python3
"""Authentication helpers for first-login flows.

Exports:
- `login(driver, user, password)`
- `set_new_password(driver, new_password)`
- `first_login(driver, logger, ...)`
- `refresh_until_loadable(...)`
"""
import logging
import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By


def login(driver, user: str = "kaapana", password: str = "admin") -> bool:
    try:
        username = driver.find_element(By.ID, "username")
        password_field = driver.find_element(By.ID, "password")
    except Exception as exc:
        raise NoSuchElementException(str(exc)) from exc

    username.send_keys(user)
    password_field.send_keys(password)
    sign_in = driver.find_element(By.ID, "kc-login")
    sign_in.click()

    try:
        driver.find_element(By.ID, "input-error")
        return False
    except Exception:
        return True


def set_new_password(driver, new_password: str = "admin") -> None:
    try:
        new_password_field = driver.find_element(By.ID, "password-new")
        confirm_password_field = driver.find_element(By.ID, "password-confirm")
    except Exception as exc:
        raise NoSuchElementException(str(exc)) from exc

    new_password_field.send_keys(new_password)
    confirm_password_field.send_keys(new_password)
    try:
        confirm_password_field._h.press("Enter")
    except Exception:
        try:
            btn = driver._page.query_selector("button[type=submit]")
            if btn:
                btn.click()
        except Exception:
            pass


def first_login(driver, logger: logging.Logger, user: str = "kaapana", default_password: str = "kaapana", new_password: str = "admin") -> bool:
    logger.info("Performing first login to Kaapana")
    if refresh_until_loadable(driver, user=user, password=default_password):
        logger.info("Setting new password")
        set_new_password(driver, new_password)
        return True
    else:
        logger.warning("Login with default credentials failed. Trying new credentials.")
        try:
            driver.refresh()
        except Exception:
            logger.exception("Error refreshing page before retrying login")
        return login(driver, user, new_password)


def refresh_until_loadable(driver, user: str = "kaapana", password: str = "admin", timeout: int = 60) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            return login(driver, user, password)
        except NoSuchElementException:
            time.sleep(2)
            try:
                driver.refresh()
            except Exception:
                pass
    return False
