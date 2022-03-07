from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import time
import json
import os


def start(platform_urls, suite_name="UI Tests", test_name="Platform Browser UI Tests"):
    username = "kaapana"
    init_password = "kaapana"
    password = "admin"

    time.sleep(800)
    for platform_url in platform_urls:
        suite_name = platform_url
        entry = {
            "suite": suite_name,
            "test": test_name,
            "step": "Starting ui tests",
            "log": "",
            "loglevel": "INFO",
            "message": "Starting...",
            "rel_file": platform_url,
        }
        yield entry

        chrome_options = Options()
        # chrome_options.add_argument("--disable-gpu")
        # chrome_options.add_argument("--no-sandbox) # linux only
        # chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('--ignore-certificate-errors')
        driver = webdriver.Chrome(options=chrome_options)
        platform_url = "https://{}".format(platform_url)
        driver.get(platform_url)
        
        # driver.save_screenshot('/home/jonas/login.png')

        delay = 10
        max_retries = 15
        retries = 0

        time.sleep(20)

        while retries <= max_retries:
            try:
                quote = WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'kc-form-login')))
                break
            except TimeoutException:
                print("Waiting for the platform to come up...")
                driver.refresh()
                retries += 1

        if retries >= max_retries:
            print("Login failed! -> login-page could not be reached!")
            entry = {
                "suite": suite_name,
                "test": test_name,
                "step": "Platform URL check",
                "log": "",
                "loglevel": "ERROR",
                "message": "Could not reach url: ",
                "rel_file": platform_url,
            }
            yield entry
            return

        entry = {
            "suite": suite_name,
            "test": test_name,
            "step": "Platform URL check",
            "log": "",
            "loglevel": "INFO",
            "message": "OK - Logging in...",
            "rel_file": platform_url,
        }
        yield entry

        time.sleep(10)

        try:
            usernameInput = driver.find_elements_by_css_selector('form input')[0]
            passwordInput = driver.find_elements_by_css_selector('form input')[1]
            usernameInput.send_keys(username)
            passwordInput.send_keys(password)
            passwordInput.send_keys(Keys.ENTER)
            try:
                first_login = "invalid" in driver.find_element_by_class_name('kc-feedback-text').text.lower()
            except:
                first_login = False

            print("FIRST LOGIN? -> {}".format(first_login))
            if first_login:
                passwordInput = driver.find_elements_by_css_selector('form input')[1]
                passwordInput.send_keys(init_password)
                passwordInput.send_keys(Keys.ENTER)

                password_1 = driver.find_elements_by_css_selector('form input')[2]
                password_2 = driver.find_elements_by_css_selector('form input')[3]
                password_1.send_keys(password)
                password_2.send_keys(password)
                password_2.send_keys(Keys.ENTER)
                time.sleep(2)

        except Exception as e:

            print("Login failed!")
            entry = {
                "suite": suite_name,
                "test": test_name,
                "step": "Login",
                "log": "",
                "loglevel": "ERROR",
                "message": "Login failed!",
                "rel_file": platform_url,
            }
            yield entry
            return

        print("Login ok!")
        entry = {
            "suite": suite_name,
            "test": test_name,
            "step": "Login",
            "log": "",
            "loglevel": "INFO",
            "message": "Login ok.",
            "rel_file": platform_url,
        }
        yield entry

        with open(os.path.abspath(__file__).replace("platform_ui_tests.py", "test_urls.json"), "r") as f:
            test_urls = json.load(f)

        for url in test_urls:
            count = 0
            while count < 5:
                count += 1

                print("Checking: {}".format(url))
                driver.get("{}/{}".format(platform_url, url["url"]))
                print(driver.title)

                # if url["url"] == "flow":
                #     table_rows=driver.find_elements_by_css_selector('table')[0].find_elements_by_css_selector('tbody')[0].find_elements_by_css_selector('tr')
                #     for row in table_rows:
                #         print(row.text.replace(" ", "\n").split("\n"))
                #     # elem = driver.find_element_by_xpath("//*")
                #     # source_code = elem.get_attribute("outerHTML")
                #     print("CHeck")

                if url["title"] in driver.title:
                    print("ok")
                    entry = {
                        "suite": suite_name,
                        "test": test_name,
                        "step": "Testing endpoint",
                        "log": "",
                        "loglevel": "INFO",
                        "message": "Endpoint ok: {}".format(url["title"]),
                        "rel_file": url["url"],
                    }
                    yield entry
                    break

                else:
                    print("WARNING: Could not get: {}".format(url["url"]))
                    if count > 2:
                        entry = {
                            "suite": suite_name,
                            "test": test_name,
                            "step": "Testing endpoint",
                            "log": "",
                            "loglevel": "WARN",
                            "message": "Problems testing: {}".format(url["title"]),
                            "rel_file": url["url"],
                        }
                        yield entry
                    time.sleep(3)

                if count >= 5:
                    print("ERROR while testing: : {}".format(url["title"]))
                    entry = {
                        "suite": suite_name,
                        "test": test_name,
                        "step": "Testing endpoint",
                        "log": "",
                        "loglevel": "ERROR",
                        "message": "Failed! Got: '{}' expected: '{}'".format(driver.title, url["title"]),
                        "rel_file": url["url"],
                    }
                    yield entry

        driver.close()
        driver.quit()

        entry = {
            "suite": suite_name,
            "test": test_name,
            "step": "Finish UI tests",
            "log": "",
            "loglevel": "INFO",
            "message": "UI tests done.",
            "rel_file": "",
            "test_done": True
        }
        yield entry


if __name__ == "__main__":
    for log in start(platform_urls=["vm-128-241.cloud.dkfz-heidelberg.de"]):
        print(json.dumps(log, indent=4, sort_keys=True))
