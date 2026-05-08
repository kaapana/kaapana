# test_first_login.py
import pytest
from integration_tests.utils.KaapanaPlaywrightDriver import KaapanaPlaywrightDriver


@pytest.mark.asyncio
async def test_first_login(driver: KaapanaPlaywrightDriver, host: str):
    await driver.goto(f"http://{host}")

    assert not await driver.login("kaapana", "admin")
    assert await driver.login("kaapana", "kaapana")

    # Set new password
    await driver.set_new_password("admin")

    await driver.reset_session()
    await driver.goto(f"http://{host}")

    # Admin password may already be set
    assert await driver.login(
        "kaapana", "admin"
    ), "Login after setting new password failed"
