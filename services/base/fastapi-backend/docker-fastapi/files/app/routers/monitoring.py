import os
from fastapi import APIRouter, Response, Depends
from app.dependencies import get_prometheus_client


router = APIRouter(tags=["monitoring"])

@router.get('/metrics')
def list_metrics(client = Depends(get_prometheus_client)):    
    """Return list of metrics that are scraped by Prometheus
    """
    return client.all_metrics()


@router.get('/metrics/cpu-usage')
def cpu_usage(client = Depends(get_prometheus_client)):    
    """Return cluster CPU Usage
    """
    return client.query("cpu-usage","sum(rate(container_cpu_usage_seconds_total{id='/',kubernetes_io_hostname=~'^.*$'}[1m]))/sum(machine_cpu_cores{kubernetes_io_hostname=~'^.*$'})*100")


@router.get('/metrics/mem-usage')
def mem_usage(client = Depends(get_prometheus_client)):
    """Return cluster memory utilization
    """
    return client.query("mem-usage","sum (container_memory_working_set_bytes{id='/',kubernetes_io_hostname=~'^.*$'}) / sum (machine_memory_bytes{kubernetes_io_hostname=~'^.*$'}) * 100")

@router.get('/query/{query}')
def custom_query(q: str, client = Depends(get_prometheus_client)):
    """Custom query
    description: Enter custom query to scrape metrics from Prometheus

    Sometimes the prometheus client library returns an empty response for a non-empty query result.
    """
    result = client.query("custom-query", q)
    if not result:
      raise HTTPException(status_code=204, detail="No content")
    else:
      return result