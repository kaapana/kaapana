import html
import os
from typing import List

from app.dependencies import get_monitoring_service
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse

from .schemas import Measurement

router = APIRouter(tags=["monitoring"])


@router.get("/metrics", response_model=List[str])
def list_metrics(client=Depends(get_monitoring_service)):
    """Return list of metrics that are scraped by Prometheus"""
    return client.all_metrics()


@router.get("/metrics/cpu-usage", response_model=Measurement)
def cpu_usage(client=Depends(get_monitoring_service)):
    """Return cluster CPU Usage"""
    return client.query(
        "cpu-usage",
        "sum(rate(container_cpu_usage_seconds_total{id='/',kubernetes_io_hostname=~'^.*$'}[1m]))/sum(machine_cpu_cores{kubernetes_io_hostname=~'^.*$'})*100",
    )


@router.get("/metrics/node-info", response_model=List[str])
def node_info(client=Depends(get_monitoring_service)):
    """Return Kaapana node metrics"""
    return client.query(
        "cpu-usage",
        "sum(rate(container_cpu_usage_seconds_total{id='/',kubernetes_io_hostname=~'^.*$'}[1m]))/sum(machine_cpu_cores{kubernetes_io_hostname=~'^.*$'})*100",
    )


@router.get("/metrics/scrape", response_class=PlainTextResponse)
def scrape(client=Depends(get_monitoring_service)):
    """Return Kaapana node metrics"""
    return client.get_node_metrics()


@router.get("/metrics/mem-usage", response_model=Measurement)
def mem_usage(client=Depends(get_monitoring_service)):
    """Return cluster memory utilization"""
    return client.query(
        "mem-usage",
        "round(sum(node_memory_MemAvailable_bytes{job='Node-Exporter'}) / sum(node_memory_MemTotal_bytes{job='Node-Exporter'}) * 100)",
    )


@router.get("/query/{query}", response_model=Measurement)
def custom_query(q: str, client=Depends(get_monitoring_service)):
    """Custom query
    description: Enter custom query to scrape metrics from Prometheus

    Sometimes the prometheus client library returns an empty response for a non-empty query result.
    """
    # The SanitizeQueryParams middleware HTML-escapes all query params, which
    # corrupts every PromQL query with quoted label values; undo it here — q
    # goes to the Prometheus HTTP API, not into an HTML context.
    result = client.query("custom-query", html.unescape(q))
    if not result:
        # 404, not 204: a 204 must not carry a body, FastAPI's exception
        # handler would crash the response.
        raise HTTPException(status_code=404, detail="No data for query")
    else:
        return result


@router.get("/query-range/{query}", response_model=List[Measurement])
def custom_query_range(
    q: str,
    minutes: int = 60,
    step: int = 60,
    client=Depends(get_monitoring_service),
):
    """Custom range query: PromQL evaluated over the last `minutes` at `step` seconds resolution."""
    result = client.query_range("custom-query-range", html.unescape(q), minutes, step)
    if not result:
        raise HTTPException(status_code=404, detail="No data for query")
    return result
