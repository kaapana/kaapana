import json
import logging
from dataclasses import asdict, dataclass
from typing import List, Optional
from xml.etree import ElementTree

import requests

log = logging.getLogger("uvicorn.error")

PREFERRED_ACTIONS = ("edit", "view")


@dataclass
class WOPIAction:
    extension: str
    name: str
    url: str


@dataclass
class WOPIApp:
    net_zone: str
    favicon: Optional[str]
    name: str
    actions: List[WOPIAction]


@dataclass
class WOPIMatch:
    app: WOPIApp
    action: WOPIAction


class WOPI:
    def __init__(self, wopi_discovery_url: str, timeout: float = 10):
        self.wopi_discovery_url = wopi_discovery_url
        self.timeout = timeout
        self.apps: list[WOPIApp] = []  # initialized by fetch_apps

    def supported_extensions(self) -> set[str]:
        return {action.extension for app in self.apps for action in app.actions}

    def match(self, extension: str) -> Optional[WOPIMatch]:
        extension = extension.lower()
        candidates = [
            WOPIMatch(app, action) for app in self.apps for action in app.actions if action.extension == extension
        ]
        if not candidates:
            return None
        for name in PREFERRED_ACTIONS:
            for candidate in candidates:
                if candidate.action.name == name:
                    return candidate
        return candidates[0]

    def fetch_apps(self) -> None:
        log.info("WOPI discovery started, fetching new apps from %s", self.wopi_discovery_url)
        response = requests.get(self.wopi_discovery_url, timeout=self.timeout)
        response.raise_for_status()
        self.apps = parse_discovery(response.content)
        log.debug("Fetched applications %s", json.dumps([asdict(app) for app in self.apps]))


def parse_discovery(content: bytes) -> list[WOPIApp]:
    tree = ElementTree.fromstring(content)
    apps = []
    for net_zone in tree.iter("net-zone"):
        net_zone_name = net_zone.attrib.get("name")
        for app in net_zone.iter("app"):
            app_name = app.attrib.get("name")
            actions = [
                WOPIAction(action.attrib["ext"].lower(), action.attrib.get("name"), action.attrib["urlsrc"])
                for action in app.iter("action")
                if action.attrib.get("ext") and action.attrib.get("urlsrc")
            ]
            if not actions:
                log.debug("WOPI app %s has no extension based action --> skipping", app_name)
                continue
            apps.append(WOPIApp(net_zone_name, app.attrib.get("favIconUrl"), app_name, actions))
    return apps


def editor_url(urlsrc: str, wopi_src: str) -> str:
    if urlsrc.endswith(("?", "&")):
        separator = ""
    elif "?" in urlsrc:
        separator = "&"
    else:
        separator = "?"
    return f"{urlsrc}{separator}WOPISrc={wopi_src}"
