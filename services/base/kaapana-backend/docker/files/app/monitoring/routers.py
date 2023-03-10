import os
from fastapi import APIRouter, Response, Depends
from fastapi.responses import PlainTextResponse
from app.dependencies import get_monitoring_service
from .schemas import Measurement
from typing import List


router = APIRouter(tags=["monitoring"])

@router.get('/metrics', response_model=List[str])
def list_metrics(client = Depends(get_monitoring_service)):
    """Return list of metrics that are scraped by Prometheus
    """
    return client.all_metrics()

@router.get('/metrics/cpu-usage', response_model=Measurement)
def cpu_usage(client = Depends(get_monitoring_service)):
    """Return cluster CPU Usage
    """
    return client.query("cpu-usage","sum(rate(container_cpu_usage_seconds_total{id='/',kubernetes_io_hostname=~'^.*$'}[1m]))/sum(machine_cpu_cores{kubernetes_io_hostname=~'^.*$'})*100")

@router.get('/metrics/node-info', response_model=List[str])
def node_info(client = Depends(get_monitoring_service)):
    """Return Kaapana node metrics
    """
    return client.query("cpu-usage","sum(rate(container_cpu_usage_seconds_total{id='/',kubernetes_io_hostname=~'^.*$'}[1m]))/sum(machine_cpu_cores{kubernetes_io_hostname=~'^.*$'})*100")

@router.get('/metrics/scrape', response_class=PlainTextResponse)
def scrape(client = Depends(get_monitoring_service)):
    """Return Kaapana node metrics
    """
    return client.get_get_node_metrics()

@router.get('/metrics/mem-usage', response_model=Measurement)
def mem_usage(client = Depends(get_monitoring_service)):
    """Return cluster memory utilization
    """
    return client.query("mem-usage","sum (container_memory_working_set_bytes{id='/',kubernetes_io_hostname=~'^.*$'}) / sum (machine_memory_bytes{kubernetes_io_hostname=~'^.*$'}) * 100")

@router.get('/query/{query}', response_model=Measurement)
def custom_query(q: str, client = Depends(get_monitoring_service)):
    """Custom query
    description: Enter custom query to scrape metrics from Prometheus

    Sometimes the prometheus client library returns an empty response for a non-empty query result.
    """
    result = client.query("custom-query", q)
    if not result:
      raise HTTPException(status_code=204, detail="No content")
    else:
      return result