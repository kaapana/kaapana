#!/usr/bin/env python3
"""
Scan a host for open ports and validate them against an allowed list.

Example:
    python scan_ports.py --host 192.168.1.10 --allowed 22,443
"""

import argparse
import logging
import sys
import nmap3
from base_utils.logger import get_logger


logger = get_logger(__name__, logging.DEBUG)


def parse_arguments():
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Scan a host for open ports and verify allowed ones.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--host",
        required=True,
        help="Host IP or hostname to scan."
    )

    parser.add_argument(
        "--allowed",
        required=True,
        help="Comma-separated list of allowed open ports (e.g., '22,443,8080')."
    )

    args = parser.parse_args()

    # Validate allowed ports
    allowed_ports = []
    for port in args.allowed.split(","):
        port = port.strip()
        if not port.isdigit():
            parser.error(f"Invalid port '{port}' in --allowed")
        allowed_ports.append(port)

    return args.host, allowed_ports


def scan_ports(host: str):
    """Run an Nmap scan on the given host and return port data."""
    nmap = nmap3.Nmap()

    try:
        results = nmap.scan_top_ports(host)
    except Exception as e:
        logger.error(f"Failed to run Nmap scan: {e}")
        sys.exit(2)

    if host not in results:
        logger.error(f"Nmap returned no results for host: {host}")
        sys.exit(2)

    return results[host].get("ports", [])


def check_ports(ports, allowed_ports):
    """Validate open ports against the allowed list."""
    open_ports = []
    success = True

    for port in ports:
        port_id = port.get("portid")
        state = port.get("state")

        logger.info(f"Port {port_id}: {state}")

        if state == "open":
            open_ports.append(port_id)
            if port_id not in allowed_ports:
                logger.error(f"Illegal open port detected: {port_id}")
                success = False

    return success, open_ports


def main():
    host, allowed_ports = parse_arguments()
    logger.info(f"Scanning host: {host}")

    ports = scan_ports(host)
    ok, open_ports = check_ports(ports, allowed_ports)

    if open_ports:
        logger.info(f"Open ports: {', '.join(open_ports)}")
    else:
        logger.info("No open ports found.")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
