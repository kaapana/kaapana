
from flask import jsonify
from . import api_v1
from prometheus_api_client import PrometheusConnect
import os
from datetime import timedelta

_prometheus_host="http://prometheus-service.monitoring.svc:9000/prometheus"
#_prometheus_host='http://127.0.0.1:9000/prometheus'
prom = PrometheusConnect(_prometheus_host)

@api_v1.route('/monitoring/metrics-list')
def list_metrics():    
    """Return list of metrics that are scraped by Prometheus
    ---
    tags:
      - Monitoring
   
    responses:
      200:
        description: List of all metrics that the Prometheus host scrapes
    """

    # Get the list of all the metrics that the Prometheus host scrapes
    metrics_list = prom.all_metrics()
    
    # # Fetch values of a particular metric name
    # metrics_list = prom.custom_query(query="prometheus_http_requests_total")
    # metrics_list = prom.custom_query(query="sum(container_cpu_usage_seconds_total)")
    # metrics_list = prom.custom_query(query="container_cpu_usage_seconds_total")
    # print(metrics_list[0]['value'][0])
    # print(str(timedelta(seconds=metrics_list[0]['value'][0])))
    print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
    
    return jsonify(metrics_list)


@api_v1.route('/monitoring/cpu-usage')
def cpu_usage():    
    """Return cluster CPU Usage
    ---
    tags:
      - Monitoring
   
    responses:
      200:
        description: Cluster CPU Usage
    """
    
    metrics_list = prom.custom_query(query="sum(rate(container_cpu_usage_seconds_total{id='/',kubernetes_io_hostname=~'^.*$'}[1m]))/sum(machine_cpu_cores{kubernetes_io_hostname=~'^.*$'})*100")

    print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
    
    return jsonify(metrics_list)


@api_v1.route('/monitoring/mem-usage')
def mem_usage():
    """Return cluster memory utilization
    ---
    tags:
      - Monitoring
   
    responses:
      200:
        description: Cluster memory utilization
    """

    metrics_list = prom.custom_query(query="sum (container_memory_working_set_bytes{id='/',kubernetes_io_hostname=~'^.*$'}) / sum (machine_memory_bytes{kubernetes_io_hostname=~'^.*$'}) * 100")

    print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
    
    return jsonify(metrics_list)


@api_v1.route('/monitoring/<string:query>')
def custom_query(query):
    """Custom query
    ---
    tags:
      - Monitoring
    parameters:
      - name: query
        in: path
        type: string
        required: true
        description: Enter custom query to scrape metrics from Prometheus
    responses:
      200:
        description: Result of user-defined query
    """

    metrics_list = prom.custom_query(query=query)

    print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
    
    return jsonify(metrics_list)



