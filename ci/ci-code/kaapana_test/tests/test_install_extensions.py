# test_install_extensions.py
import asyncio
import json
import logging
import time

import pytest

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_install_extension(
    extension, extension_endpoint, json_extension_params, timeout
):
    """Install a single extension."""
    poll_interval = 5

    try:
        with open(json_extension_params) as f:
            extension_params = json.load(f)
    except FileNotFoundError:
        extension_params = {}

    chart_name = extension.get("chart_name")
    logger.info(f"Testing extension installation: {chart_name}")

    # -------------------------------
    # INSTALL
    # -------------------------------
    _, failed = extension_endpoint.install_extensions([extension], extension_params)
    assert not failed, f"Failed to initiate installation for: {failed}"

    start = time.time()
    while time.time() - start < timeout:
        if extension_endpoint.extension_is_installed(extension):
            total_elapsed = time.time() - start
            logger.info(
                f"Extension {chart_name} installed successfully in ~{total_elapsed:.2f} seconds."
            )
            break
        logger.info(f"Waiting for extension {chart_name} to install...")
        await asyncio.sleep(poll_interval)
    else:
        pytest.fail(f"Timeout: Extension {chart_name} not installed")
