from .kaapana_chrome_driver import (
    KaapanaChromeDriver,
    KaapanaRemoteDriver,
)
import os

if (test_locally := os.getenv("TEST_LOCALLY")) and test_locally.lower() == "true":
    MainDriver = KaapanaChromeDriver()
else:
    MainDriver = KaapanaRemoteDriver()
