from pprint import pprint
import requests
import time
import logging
import os

SERVICES_NAMESPACE = os.getenv("SERVICES_NAMESPACE", None)
assert SERVICES_NAMESPACE

prometheus_base_url = (
    f"http://prometheus-service.{SERVICES_NAMESPACE}.svc:9090/prometheus/api/v1/query"
)
prometheus_url = f"{prometheus_base_url}?query="

memory_query = "floor(node_memory_MemTotal_bytes{job='Node-Exporter'}/1048576)"
mem_util_per_query = "sum(node_memory_MemTotal_bytes{job='Node-Exporter'} - node_memory_MemAvailable_bytes{job='Node-Exporter'}) / sum(node_memory_MemTotal_bytes{job='Node-Exporter'})"
query_memory_requested_from_pods_in_services_namespace = 'round(sum(kube_pod_container_resource_requests{unit="byte",namespace="services"})/1000000) * on (namespace, pod) group_left() (kube_pod_status_phase{namespace="services", phase="Running"} == 1)) / 1e6'
query_memory_requested_from_pods_in_admin_namespace = 'round(sum(kube_pod_container_resource_requests{unit="byte",namespace="admin"})/1000000)  * on (namespace, pod) group_left() (kube_pod_status_phase{namespace="admin", phase="Running"} == 1)) / 1e6'


cpu_core_query = "machine_cpu_cores"
cpu_util_per_query = 'sum (rate (container_cpu_usage_seconds_total{id="/"}[1m])) / sum (machine_cpu_cores) * 100'
cpu_util_cores_used_query = 'sum(rate (container_cpu_usage_seconds_total{id="/"}[1m]))'

gpu_count_query = (
    "count(DCGM_FI_DEV_POWER_USAGE{kubernetes_name='nvidia-dcgm-exporter'})"
)
gpu_mem_used_device_query = (
    "DCGM_FI_DEV_FB_USED{kubernetes_name='nvidia-dcgm-exporter',gpu=~'<replace>'}"
)
gpu_mem_available_device_query = (
    "DCGM_FI_DEV_FB_FREE{kubernetes_name='nvidia-dcgm-exporter',gpu=~'<replace>'}"
)
gpu_infos_query_memory = (
    '{__name__=~"DCGM_FI_DEV_FB_(FREE|USED|RESERVED)",app="nvidia-dcgm-exporter"}'
)


def get_node_info(query, logger=logging):
    tries = 0
    max_tries = 4
    result_value = None
    success = True
    while result_value == None and tries < max_tries:
        try:
            request_url = f"{prometheus_url}{query}"
            response = requests.get(request_url, timeout=1)
            result = response.json()["data"]["result"]
        except:
            return 0, False
        if isinstance(result, list) and len(result) > 0:
            result_value = int(float(response.json()["data"]["result"][0]["value"][1]))
        elif "nvidia" in query:
            result_value = 0
        else:
            time.sleep(1)
            tries += 1
    if tries >= max_tries:
        logger.error(f"+++++++++ Could not fetch node-info for query: {query}")
        success = False

    if not isinstance(result_value, int):
        result_value = 0

    return result_value, success


def get_node_gpu_infos(logger=logging):
    try:
        response = requests.get(
            prometheus_base_url,
            params={"query": gpu_infos_query_memory},
            timeout=1,
        )
        result = response.json()
    except:
        logger.error(f"+++++++++ Could not fetch node-info for GPUs - requests failed")
        return []

    if "status" not in result or result["status"] != "success":
        logger.error(f"+++++++++ Could not fetch node-info for GPUs - success != true")
        return []

    gpu_metrics = {}
    for gpu_info in result["data"]["result"]:
        metric = gpu_info["metric"]
        gpu_uuid = metric.get("UUID")
        if gpu_uuid is None:
            logger.warning(f"Ignoring GPU metric without UUID: {metric}")
            continue

        gpu = gpu_metrics.setdefault(
            gpu_uuid,
            {
                "node": metric["Hostname"],
                "gpu_id": metric["gpu"],
                "gpu_uuid": gpu_uuid,
                "pool_id": f"NODE_GPU_{metric['gpu']}_MEM",
                "gpu_name": metric["modelName"],
            },
        )
        value = int(float(gpu_info["value"][1]))

        if metric["__name__"] == "DCGM_FI_DEV_FB_FREE":
            gpu["free"] = value
        elif metric["__name__"] == "DCGM_FI_DEV_FB_USED":
            gpu["used"] = value
        elif metric["__name__"] == "DCGM_FI_DEV_FB_RESERVED":
            gpu["reserved"] = value

    gpu_list = []
    for gpu in gpu_metrics.values():
        if "free" not in gpu or "used" not in gpu:
            logger.warning(f"Ignoring GPU with incomplete memory metrics: {gpu}")
            continue

        reserved = gpu.get("reserved", 0)
        gpu_list.append(
            {
                **gpu,
                "reserved": reserved,
                "capacity": gpu["free"] + gpu["used"] + reserved,
                "queued_count": 0,
                "queued_mb": 0,
            }
        )

    gpu_list = sorted(gpu_list, key=lambda d: d["capacity"])
    return gpu_list


def get_node_memory(logger=None):
    node_memory, success = get_node_info(query=memory_query)
    if not success:
        if logger != None:
            logger.error(f"+++++++++ Could not fetch node-info: get_node_memory")
        return None

    return node_memory


def get_node_requested_memory(logger=None):
    """
    Get the sum of all memory requests by pods in the namespaces services and admin.
    """
    memory_requested_from_pods_in_services_namespace, success1 = get_node_info(
        query=query_memory_requested_from_pods_in_services_namespace
    )
    memory_requested_from_pods_in_admin_namespace, success2 = get_node_info(
        query=query_memory_requested_from_pods_in_admin_namespace
    )

    if not success1 or not success2:
        if logger != None:
            logger.error(
                f"+++++++++ Could not fetch node-info: get_node_requested_memory"
            )
        return None

    return (
        memory_requested_from_pods_in_services_namespace
        + memory_requested_from_pods_in_admin_namespace
    )


def get_node_mem_percent(logger=None):
    mem_percent, success = get_node_info(query=mem_util_per_query)
    if not success:
        if logger != None:
            logger.error(f"+++++++++ Could not fetch node-info: get_node_mem_percent")
        return None

    return mem_percent


def get_node_cpu(logger=None):
    node_cpu, success = get_node_info(query=cpu_core_query)
    if not success:
        if logger != None:
            logger.error(f"+++++++++ Could not fetch node-info: get_node_cpu")
        return None

    return node_cpu


def get_node_cpu_util_percent(logger=None):
    cpu_util_per, success = get_node_info(query=cpu_util_per_query)
    if not success:
        if logger != None:
            logger.error(
                f"+++++++++ Could not fetch node-info: get_node_cpu_util_percent"
            )
        return None

    return cpu_util_per
