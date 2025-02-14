import requests
import logging
import json

from xml.etree import ElementTree
from typing import List

from dataclasses import dataclass, asdict
from requests.adapters import HTTPAdapter, Retry

log = logging.getLogger("uvicorn.error")


@dataclass
class WOPIAction:
    extension: str
    name: str
    url: str


@dataclass
class WOPIApp:
    net_zone: str
    favicon: str
    name: str
    actions: List[WOPIAction]


class WOPI:
    def __init__(self, wopi_discovery_url):
        self.wopi_discovery_url = wopi_discovery_url
        self.apps: list(WOPIApp) = []  # initialized by fetch_apps

    def supported_extensions(self):
        for app in self.apps:
            for action in app.actions:
                yield action.extension

    def get_url(self, extension: str) -> str:
        for app in self.apps:
            for action in app.actions:
                if action.extension.lower() == extension.lower():
                    return action.url

    def get_apps_actions_for_files(self, extension: str):
        for app in self.apps:
            for action in app.actions:
                actions = []
                if action.extension.lower() == extension.lower():
                    actions.append(action)
                if actions:
                    custom_app = WOPIApp(**asdict(app))
                    custom_app.actions = actions
                    yield custom_app

    def fetch_apps(self) -> None:
        log.info(
            "WOPI discovery started, fetching new apps form %s", self.wopi_discovery_url
        )
        s = requests.Session()

        # TODO: more robust reconnects
        retries = Retry(
            total=1000, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504]
        )

        s.mount("http://", HTTPAdapter(max_retries=retries))
        response = s.get(self.wopi_discovery_url)
        response.raise_for_status()
        log.debug(
            "fetched %s with stats code %i",
            self.wopi_discovery_url,
            response.status_code,
        )

        # Parsing XML Response in WOPIApps
        tree = ElementTree.fromstring(response.content)
        apps = []
        for net_zone in tree:
            net_zone_name = net_zone.attrib.get("name")
            for app in net_zone:
                favicon = app.attrib.get("favIconUrl")
                app_name = app.attrib.get("name")
                actions = []
                for action in app:
                    extension = action.attrib.get("ext")
                    name = action.attrib.get("name")
                    url = action.attrib.get("urlsrc")
                    actions.append(WOPIAction(extension, name, url))
                if not actions:
                    log.warning(
                        "WOPI app %s returned no actoin in %s --> skipping",
                        name,
                        self.wopi_discovery_url,
                    )
                    continue
                apps.append(WOPIApp(net_zone_name, favicon, app_name, actions))

        log.debug("Fetched applications %s", json.dumps([asdict(app) for app in apps]))
        self.apps = apps
