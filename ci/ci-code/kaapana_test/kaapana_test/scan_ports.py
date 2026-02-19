#!/usr/bin/env python3
import logging
import sys


def scan_ports(ip_address: str, logger: logging.Logger):
    """Run an Nmap scan on the given host and return port data."""
    try:
        import nmap3
    except ImportError:
        logger.error(
            "Required Python package 'nmap3' is not installed."
            " Install it with: `pip install nmap3` or `pip install -r requirements.txt`."
            " Also ensure the system 'nmap' binary is installed (e.g. `apt-get install nmap`)."
        )
        sys.exit(2)

    nmap = nmap3.Nmap()

    try:
        results = nmap.scan_top_ports(ip_address)
    except Exception as e:
        logger.error(f"Failed to run Nmap scan: {e}")
        sys.exit(2)

    if ip_address not in results:
        logger.error(f"Nmap returned no results for host: {ip_address}")
        sys.exit(2)

    return results[ip_address].get("ports", [])


def check_ports(ports, allowed_ports, logger: logging.Logger):
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
