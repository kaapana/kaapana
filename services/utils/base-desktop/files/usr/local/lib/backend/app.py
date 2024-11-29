import asyncio
import logging
import subprocess

from fastapi import FastAPI, HTTPException, Query

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI()


def configure_size(width: int, height: int) -> bool:
    """
    Modifies the /usr/local/bin/xvfb.sh script to update the Xvfb configuration.

    Args:
        width (int): Width for the screen resolution.
        height (int): Height for the screen resolution.
    """
    command = (
        "sed -i 's#"
        "^exec /usr/bin/Xvfb.*$"
        "#"
        "exec /usr/bin/Xvfb :1 -screen 0 {}x{}x24"
        "#' /usr/local/bin/xvfb.sh"
    ).format(width, height)

    try:
        subprocess.run(command, shell=True, check=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False


def state_health() -> bool:
    """
    Check the health of services managed by Supervisor.

    Returns:
        bool: True if all required services are running, False otherwise.
    """
    try:
        output = subprocess.run(
            ["supervisorctl", "-c", "/etc/supervisor/supervisord.conf", "status"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        log.debug("Supervisor status retreived successfully.")
    except subprocess.CalledProcessError as e:
        log.error(f"Failed to check Supervisor status: {e}")
        return False

    # Check if all lines indicate a running service
    for line in output.strip().split("\n"):
        if not line.startswith("web") and "RUNNING" not in line:
            log.debug("Not running services in line '%s'", line)
            return False
    return True


async def wait_for_services(timeout: int = 40, interval: int = 1) -> bool:
    """
    Wait for services to become ready within a specified timeout.

    Args:
        timeout (int): Maximum number of seconds to wait.
        interval (int): Interval in seconds between health checks.

    Returns:
        bool: True if services become ready within the timeout, False otherwise.
    """
    for i in range(timeout):
        if state_health():
            log.debug("All services are running.")
            return True
        await asyncio.sleep(interval)
        log.debug(f"Waiting for services to be ready... Attempt {i + 1}/{timeout}")
    return False


async def restart_desktop():
    """
    Restart the Supervisor desktop service asynchronously and check the health of services.
    """
    try:
        # Restart Supervisor
        subprocess.run(
            [
                "supervisorctl",
                "-c",
                "/etc/supervisor/supervisord.conf",
                "restart",
                "x:",
            ],
            check=True,
            text=True,
        )
        log.info("Supervisor restart triggered successfully.")
    except subprocess.CalledProcessError as e:
        log.error(f"Failed to restart Supervisor: {e}")
        raise HTTPException(status_code=500, detail="Failed to restart Supervisor")

    return await wait_for_services()


# TODO current way of resizing kills all applications, make sure that this only happens once on inital connect
resized = False


@app.get("/resize", status_code=204)
async def resize(width: int = Query(..., ge=1), height: int = Query(..., ge=1)):
    """
    Resize endpoint that accepts width and height as query parameters.

    Args:
        width (int): The new width (must be a positive integer).
        height (int): The new height (must be a positive integer).

    Returns:
        dict: A dictionary confirming the new dimensions.
    """
    global resized
    if not resized:
        resized = True
    else:
        log.info("Ignoring resize request")
        return

    if width <= 0 or height <= 0:
        raise HTTPException(
            status_code=400, detail="Width and height must be positive integers."
        )

    if not configure_size(width, height):
        raise HTTPException(412, "Could not configure new size")

    if not await restart_desktop():
        raise HTTPException(412, "Could not restart desktop")

    return {"message": "Resize operation successful.", "width": width, "height": height}
