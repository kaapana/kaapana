#!/usr/bin/env python3
import logging

from integration_tests.scan_ports import check_ports, scan_ports
from integration_tests.utils.logger import get_logger

logger = get_logger(__name__, logging.DEBUG)


def test_scan_ports(ip_address, allowed_ports):
    logger.info(f"Scanning host IP: {ip_address}")

    scanned_ports = scan_ports(ip_address, logger)
    ok, open_ports = check_ports(scanned_ports, allowed_ports, logger)

    if open_ports:
        logger.info(f"Open ports found: {', '.join(open_ports)}")
    else:
        logger.info("No open ports found.")

    assert ok, (
        f"Unexpected open ports on {ip_address}! "
        f"Allowed: {allowed_ports}, Found: {open_ports}"
    )
