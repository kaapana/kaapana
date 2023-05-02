from typing import List
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

    def es_query(query):
        _opensearchhost = f"opensearch-service.{settings.services_namespace}.svc:9200"
        os_client = OpenSearch(hosts=_opensearchhost)
        try:
            res = os_client.search(
                index="meta-index",
                body=query,
                size=10000,
                from_=0,
                request_timeout=10,
            )
            return True, res
        except Exception as e:
            print(f"Error requesting OS: {e}")
            return False, None

    def query_prom(query, return_type="int"):
        try:
            prom_result = MonitoringService.prom.custom_query(query=query)
            if return_type == "int":
                if len(prom_result) > 0 and "value" in prom_result[0]:
                    return int(prom_result[0]["value"][1])
                else:
                    return 0
                
            elif return_type == "float":
                return float(prom_result[0]["value"][1])
            elif return_type == "raw":
                return prom_result
            else:
                raise Exception

        except Exception as e:
            print(f"Error requesting Prometheus: {query}")
            print(str(e))
            if return_type == "int" or return_type == "float":
                return -1
            elif return_type == "raw":
                return []
            else:
                return None

    def get_modaility_series_count(modality):
        modality_query = {
            "aggs": {
                "1": {
                    "cardinality": {
                        "field": "0020000D SeriesInstanceUID_keyword.keyword"
                    }
                }
            },
            "size": 0,
            "stored_fields": ["*"],
            "query": {
                "bool": {
                    "filter": [
                        {
                            "match_phrase": {
                                "00080060 Modality_keyword.keyword": modality
                            }
                        }
                    ]
                }
            },
        }
        success, es_result = MonitoringService.es_query(query=modality_query)
        if success:
            modality_series_count = es_result["hits"]["total"]["value"]
            return modality_series_count
        else:
            return -1

    def get_study_series_patient_count():
        study_series_patient_count_query = {
            "aggs": {
                "1": {
                    "cardinality": {
                        "field": "0020000D StudyInstanceUID_keyword.keyword"
                    }
                },
                "2": {
                    "cardinality": {
                        "field": "0020000E SeriesInstanceUID_keyword.keyword"
                    }
                },
                "3": {
                    "cardinality": {
                        "field": "00100010 PatientName_keyword_alphabetic.keyword"
                    }
                },
            },
            "size": 0,
            "stored_fields": ["*"],
            "query": {"bool": {"filter": [], "should": [], "must_not": []}},
        }
        success, es_result = MonitoringService.es_query(
            query=study_series_patient_count_query
        )
        if success:
            study_count = es_result["aggregations"]["1"]["value"]
            series_count = es_result["aggregations"]["2"]["value"]
            patient_count = es_result["aggregations"]["3"]["value"]
            return series_count, study_count, patient_count
        else:
            return -1, -1, -1

    def get_node_metrics(self) -> bytes:
        registry = CollectorRegistry()

        i = Info("component_build", "Component Build Information.", registry=registry)
        i.info(
            {
                "software_version": str(settings.kaapana_build_version),
                "build_timestamp": str(settings.kaapana_build_timestamp),
                "build_branch": str(settings.kaapana_platform_build_branch),
                "deployment_timestamp": str(settings.kaapana_deployment_timestamp),
                "scrape_timestamp": datetime.now()
                .astimezone()
                .replace(microsecond=0)
                .isoformat(),
                "last_commit_timestamp": str(
                    settings.kaapana_platform_last_commit_timestamp
                ),
            }
        )

        component_uptime_seconds = MonitoringService.query_prom(
            query="round(time() - process_start_time_seconds{job='oAuth2-proxy'})",
            return_type="int",
        )
        g = Gauge(name="component_uptime_seconds", documentation="Number of seconds the system is running.", registry=registry)
        g.set(component_uptime_seconds)

        (
            number_series_total,
            number_studies_total,
            number_patiens_total,
        ) = MonitoringService.get_study_series_patient_count()

        dicom_studies_total = Gauge(
            name="dicom_studies_total",
            documentation="Number of individual DICOM studies stored in the component.",
            labelnames=["modality"],
            registry=registry,
        )
        dicom_studies_total.labels("total").set(number_studies_total)

        dicom_patients_total = Gauge(
            name="dicom_patients_total",
            documentation="Number of individual patients stored in the component.",
            labelnames=["modality"],
            registry=registry,
        )
        dicom_patients_total.labels("total").set(number_patiens_total)
        
        dicom_series_total = Gauge(
            name="dicom_series_total",
            documentation="Number of individual series stored in the component.",
            labelnames=["modality"],
            registry=registry,
        )
        dicom_series_total.labels("total").set(number_series_total)
        

        number_patiens_ct = MonitoringService.get_modaility_series_count(modality="CT")
        dicom_series_total.labels("CT").set(number_patiens_ct)
        number_patiens_mr = MonitoringService.get_modaility_series_count(modality="MR")
        dicom_series_total.labels("MR").set(number_patiens_mr)
        number_patiens_ot = MonitoringService.get_modaility_series_count(modality="OT")
        dicom_series_total.labels("OT").set(number_patiens_ot)
        number_patiens_seg = MonitoringService.get_modaility_series_count(modality="SEG")
        dicom_series_total.labels("SEG").set(number_patiens_seg)

        system_load_24h_percent = MonitoringService.query_prom(
            query="100-(avg(rate(node_cpu_seconds_total{job='Node-Exporter',mode='idle'}[24h]))*100)",
            return_type="float",
        )
        g = Gauge(
            name="system_load_24h_percent", documentation="A load indicator for the system indicating the system load over the last 24 hours in percent.", registry=registry
        )
        g.set(system_load_24h_percent)

        storage_size_total_bytes = Gauge(
            name="storage_size_total_bytes",
            documentation="The total size in bytes of the persistent storage the component has available (Labels specify the corresponding mount points).",
            labelnames=["mount_point"],
            registry=registry,
        )
        storage_size_free_bytes = Gauge(
            name="storage_size_free_bytes",
            documentation="The free size in bytes of the persistent storage the component has available (specifying the corresponding mount points).",
            labelnames=["mount_point"],
            registry=registry,
        )

        for idx, mount_point in enumerate(settings.mount_points):
            total_query = f"node_filesystem_size_bytes{{app_kubernetes_io_managed_by='',fstype!='tmpfs',mountpoint='{mount_point}'}}"
            storage_size_total = MonitoringService.query_prom(
                query=total_query, return_type="int"
            )
            free_query = f"node_filesystem_avail_bytes{{app_kubernetes_io_managed_by='',fstype!='tmpfs',mountpoint='{mount_point}'}}"
            storage_size_free = MonitoringService.query_prom(
                query=free_query, return_type="int"
            )
            storage_size_total_bytes.labels(mount_point).set(storage_size_total)
            storage_size_free_bytes.labels(mount_point).set(storage_size_free)

        
        
        jobs_success_total = MonitoringService.query_prom(
            query="af_agg_ti_successes", return_type="int"
        )
        g = Gauge(
            name="jobs_success_total",
            documentation="The number of jobs the component has processed successfully.",
            registry=registry,
        )
        g.set(jobs_success_total)

        jobs_failed_total = MonitoringService.query_prom(
            query="af_agg_ti_failures", return_type="int"
        )
        g = Gauge(
            name="jobs_failed_total",
            documentation="The number of jobs the component has failed to process.",
            registry=registry,
        )
        g.set(jobs_failed_total)

        jobs_queued_total = MonitoringService.query_prom(
            query="airflow_scheduler_tasks_executable", return_type="int"
        )
        g = Gauge(
            name="jobs_queued_total",
            documentation="The number of jobs in about to be executed (aka worklist).",
            registry=registry,
        )
        g.set(jobs_queued_total)


        workflow_avg_execution_time_seconds = Gauge(
            name="workflow_avg_execution_time_seconds",
            documentation="The number of jobs in about to be executed (aka worklist).",
            labelnames=["workflow"],
            registry=registry,
        )
        dag_avg_execution_time_seconds = MonitoringService.query_prom(
            query="af_agg_dag_processing_duration_sum", return_type="raw"
        )
        for dag_metrics in dag_avg_execution_time_seconds:
            dag_id = dag_metrics["metric"]["dag_file"]
            avg_time = int(float(dag_metrics["value"][1]))
            if "dag_" in dag_id:
                workflow_avg_execution_time_seconds.labels(dag_id).set(avg_time)

        return generate_latest(registry=registry)
