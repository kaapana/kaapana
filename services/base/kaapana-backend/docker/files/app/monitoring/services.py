import requests
import json
import logging
from typing import List
from datetime import datetime
from prometheus_api_client import PrometheusConnect
from prometheus_client import CollectorRegistry, Info, generate_latest
from .schemas import Measurement
from ..config import settings


class MonitoringService:
    def __init__(self, prometheus_url: str):
        self.prometheus_url = prometheus_url
        self.con = PrometheusConnect(self.prometheus_url, disable_ssl=True)

    def query(self, name: str, q: str) -> Measurement:
        result = self.con.custom_query(query=q)
        if not result:
            return None
        return Measurement(
            metric=name,
            value=float(result[0]["value"][1]),
            timestamp=datetime.fromtimestamp(result[0]["value"][0]),
        )

    def all_metrics(self) -> List[str]:
        return self.con.all_metrics()

    def generate_scrape_info(self) -> bytes:
        registry = CollectorRegistry()
        i = Info(
            "kaapana_build_info", "Build information of Kaapana.", registry=registry
        )
        i.info(
            {
                "kaapana_build_timestamp": str(settings.kaapana_build_timestamp),
                "kaapana_build_version": str(settings.kaapana_build_version),
                "kaapana_platform_build_branch": str(
                    settings.kaapana_platform_build_branch
                ),
                "kaapana_platform_last_commit_timestamp": str(
                    settings.kaapana_platform_last_commit_timestamp
                ),
            }
        )
        return generate_latest(registry=registry)

    def node_metrics(self) -> List[str]:
        return self.con.all_metrics()
