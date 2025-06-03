"""
Test open ports of a host.
The host that is tested is read from the environment variable ip_address.
The port ids which are allowed to be open is read from the environment variable ALLOWED_PORTS which has to be a comma-separated list of port ids.
"""
import nmap3
from base_utils.logger import get_logger
import logging, os, sys

logger = get_logger("__main__", logging.DEBUG)


host = os.environ["ip_address"]
allowed_ports = os.environ["ALLOWED_PORTS"].split(",")

nmap = nmap3.Nmap()
results = nmap.scan_top_ports(host)

ports = results[host]["ports"]
open_ports = []
for port in ports:
    portid = port["portid"]
    portstate = port["state"]
    logger.info(f"{portid}: {portstate}")
    if portstate == "open":
        open_ports.append(portid)
        if portid not in allowed_ports:
            logger.error(f"Illegal port state: {portid} in state {portstate}")
            sys.exit(1)


logger.info("Open ports: {}.".format(", ".join(open_ports)))