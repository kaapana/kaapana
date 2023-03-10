from typing import List
from datetime import datetime
from .schemas import Measurement
from datetime import datetime
from opensearchpy import OpenSearch
from app.config import settings
from prometheus_api_client import PrometheusConnect
from prometheus_client import CollectorRegistry, Info, Gauge, generate_latest

class MonitoringService:
    prom = PrometheusConnect(url=settings.prometheus_url, disable_ssl=True)

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

    def get_os_info():
        _opensearchhost = f"opensearch-service.{settings.services_namespace}.svc:9200"
        os_client = OpenSearch(hosts=_opensearchhost)
        study_series_patient_count_query = {
            "aggs": {
                "1": {
                    "cardinality": {
                        "field": "0020000D StudyInstanceUID_keyword.keyword"
                    }
                },
                "4": {
                    "cardinality": {
                        "field": "0020000E SeriesInstanceUID_keyword.keyword"
                    }
                },
                "6": {
                    "cardinality": {
                        "field": "00100010 PatientName_keyword_alphabetic.keyword"
                    }
                },
            },
            "size": 0,
            "stored_fields": ["*"],
            "query": {"bool": {"filter": [], "should": [], "must_not": []}},
        }
        try:
            res = os_client.search(
                index="meta-index",
                body=study_series_patient_count_query,
                size=10000,
                from_=0,
                request_timeout=10,
            )
            series_count = res["aggregations"]["1"]["value"]
            study_count = res["aggregations"]["4"]["value"]
            patient_count = res["aggregations"]["6"]["value"]
            return series_count, study_count, patient_count
        except Exception as e:
            print(f"Error requesting OS: {e}")
            return 0, 0, 0

    def prom_query_int(query):
        try:
            return int(MonitoringService.prom.custom_query(query=query)[0]["value"][1])
        except Exception as e:
            return -1

    def get_get_node_metrics(self) -> bytes:
        registry = CollectorRegistry()

        # timestamp = datetime.now().strftime("%Y-%m-%d %H%M%S%f")
        i = Info("kaapana_build", "Build information of Kaapana.", registry=registry)
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
        uptime_seconds = int(
            MonitoringService.prom_query_int(
                query="round(time() - process_start_time_seconds{job='oAuth2-proxy'})"
            )
        )
        g = Gauge("uptime_seconds", "uptime_seconds", registry=registry)
        g.set(uptime_seconds)
        kaapana_success_jobs = MonitoringService.prom_query_int(
            query="af_agg_ti_successes"
        )
        g = Gauge("kaapana_success_jobs", "kaapana_success_jobs", registry=registry)
        g.set(kaapana_success_jobs)
        kaapana_fail_jobs = MonitoringService.prom_query_int(query="af_agg_ti_failures")
        g = Gauge("kaapana_fail_jobs", "kaapana_fail_jobs", registry=registry)
        g.set(kaapana_fail_jobs)

        series_count, study_count, patient_count = MonitoringService.get_os_info()
        g = Gauge("series_count", "series_count", registry=registry)
        g.set(series_count)
        g = Gauge("study_count", "study_count", registry=registry)
        g.set(study_count)
        g = Gauge("patient_count", "patient_count", registry=registry)
        g.set(patient_count)
        kaapana_root_drive_size = MonitoringService.prom_query_int(
                query="node_filesystem_size_bytes{mountpoint='/',fstype!='rootfs'}"
            )
        
        g = Gauge(
            "kaapana_root_drive_size", "kaapana_root_drive_size", registry=registry
        )
        g.set(kaapana_root_drive_size)
        kaapana_root_drive_available = MonitoringService.prom_query_int(
                query="node_filesystem_avail_bytes{mountpoint='/',fstype!='rootfs'}"
            
        )
        g = Gauge(
            "kaapana_root_drive_available",
            "kaapana_root_drive_available",
            registry=registry,
        )
        g.set(kaapana_root_drive_available)
        kaapana_root_drive_percent_available = (
            -1
            if kaapana_root_drive_size < 0 or kaapana_root_drive_available < 0
            else kaapana_root_drive_available // (kaapana_root_drive_size // 100)
        )
        g = Gauge(
            "kaapana_root_drive_percent_available",
            "kaapana_root_drive_percent_available",
            registry=registry,
        )
        g.set(kaapana_root_drive_percent_available)

        kaapana_root_drive_percent_used = (
            -1
            if kaapana_root_drive_size < 0 or kaapana_root_drive_available < 0
            else 100 - kaapana_root_drive_percent_available
        )
        g = Gauge(
            "kaapana_root_drive_percent_used",
            "kaapana_root_drive_percent_used",
            registry=registry,
        )
        g.set(kaapana_root_drive_percent_used)

        kaapana_home_drive_size = int(
            MonitoringService.prom_query_int(
                query="node_filesystem_size_bytes{mountpoint='/home',fstype!='rootfs'}"
            )
        )
        g = Gauge(
            "kaapana_home_drive_size", "kaapana_home_drive_size", registry=registry
        )
        g.set(kaapana_home_drive_size)

        kaapana_home_drive_available = int(
            MonitoringService.prom_query_int(
                query="node_filesystem_avail_bytes{mountpoint='/home',fstype!='rootfs'}"
            )
        )
        g = Gauge(
            "kaapana_home_drive_available",
            "kaapana_home_drive_available",
            registry=registry,
        )
        g.set(kaapana_home_drive_available)
        kaapana_home_drive_percent_available = (
            -1
            if kaapana_home_drive_size < 0 or kaapana_home_drive_available < 0
            else kaapana_home_drive_available // (kaapana_home_drive_size // 100)
        )
        g = Gauge(
            "kaapana_home_drive_percent_available",
            "kaapana_home_drive_percent_available",
            registry=registry,
        )
        g.set(kaapana_home_drive_percent_available)

        kaapana_home_drive_percent_used = (
            -1
            if kaapana_home_drive_size < 0 or kaapana_home_drive_available < 0
            else 100 - kaapana_home_drive_percent_available
        )
        g = Gauge(
            "kaapana_home_drive_percent_used",
            "kaapana_home_drive_percent_used",
            registry=registry,
        )
        g.set(kaapana_home_drive_percent_used)

        kaapana_data_drive_size = int(
            MonitoringService.prom_query_int(
                query="node_filesystem_size_bytes{mountpoint='/data',fstype!='rootfs'}"
            )
        )
        g = Gauge(
            "kaapana_data_drive_size", "kaapana_data_drive_size", registry=registry
        )
        g.set(kaapana_data_drive_size)

        kaapana_data_drive_available = int(
            MonitoringService.prom_query_int(
                query="node_filesystem_avail_bytes{mountpoint='/data',fstype!='rootfs'}"
            )
        )
        g = Gauge(
            "kaapana_data_drive_available",
            "kaapana_data_drive_available",
            registry=registry,
        )
        g.set(kaapana_data_drive_available)

        kaapana_data_drive_percent_available = (
            -1
            if kaapana_data_drive_size < 0 or kaapana_data_drive_available < 0
            else kaapana_data_drive_available // (kaapana_data_drive_size // 100)
        )
        g = Gauge(
            "kaapana_data_drive_percent_available",
            "kaapana_data_drive_percent_available",
            registry=registry,
        )
        g.set(kaapana_data_drive_percent_available)

        kaapana_data_drive_percent_used = (
            -1
            if kaapana_data_drive_size < 0 or kaapana_data_drive_available < 0
            else 100 - kaapana_data_drive_percent_available
        )
        g = Gauge(
            "kaapana_data_drive_percent_used",
            "kaapana_data_drive_percent_used",
            registry=registry,
        )
        g.set(kaapana_data_drive_percent_used)

        return generate_latest(registry=registry)
