import requests
import json
import logging
from typing import List
from datetime import datetime
from prometheus_api_client import PrometheusConnect
from .schemas import Measurement

class MonitoringService:
    def __init__(self, prometheus_url: str):
        self.prometheus_url = prometheus_url
        self.con = PrometheusConnect(self.prometheus_url)

    def query(self, name: str, q: str) -> Measurement:
        result = self.con.custom_query(query=q)
        if not result:
            return None
        return Measurement(metric=name,
                value=float(result[0]['value'][1]),
                timestamp=datetime.fromtimestamp(result[0]['value'][0]))

    def all_metrics(self) -> List[str]:
        return self.con.all_metrics()