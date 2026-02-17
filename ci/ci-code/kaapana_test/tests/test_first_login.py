# test_first_login_async.py
import pytest


@pytest.mark.asyncio
async def test_invalid_login(driver, host):
    await driver.goto(f"http://{host}")
    ok = await driver.login("kaapana", "invalid")
    assert not ok, "Login with invalid credentials should fail"


@pytest.mark.asyncio
async def test_first_login(driver, host):
    await driver.goto(f"http://{host}")

    # Wrong password must fail
    assert not await driver.login("kaapana", "kaapana")

    # Admin password may already be set
    if await driver.login("kaapana", "admin"):
        # Password already set, first-login flow done
        return

    # Set new password
    await driver.set_new_password("admin")
    assert await driver.login(
        "kaapana", "admin"
    ), "Login after setting new password failed"
