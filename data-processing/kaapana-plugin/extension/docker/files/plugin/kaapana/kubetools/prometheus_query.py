from pprint import pprint
import requests
import time
import logging
import os
import json

SERVICES_NAMESPACE = os.getenv('SERVICES_NAMESPACE', None)
assert SERVICES_NAMESPACE

prometheus_url = f"http://prometheus-service.{SERVICES_NAMESPACE}.svc:9090/prometheus/api/v1/query?query="

memory_query = "floor(sum(machine_memory_bytes)/1048576)"
mem_util_per_query = "sum (container_memory_working_set_bytes{id=\"/\"}) / sum (machine_memory_bytes) * 100"

cpu_core_query = "machine_cpu_cores"
cpu_util_per_query = "sum (rate (container_cpu_usage_seconds_total{id=\"/\"}[1m])) / sum (machine_cpu_cores) * 100"
cpu_util_cores_used_query = "sum(rate (container_cpu_usage_seconds_total{id=\"/\"}[1m]))"

gpu_count_query = "count(DCGM_FI_DEV_POWER_USAGE{kubernetes_name='nvidia-dcgm-exporter'})"
gpu_mem_used_device_query = "DCGM_FI_DEV_FB_USED{kubernetes_name='nvidia-dcgm-exporter',instance=~'.+',gpu=~'<replace>'}"
gpu_mem_available_device_query = "DCGM_FI_DEV_FB_FREE{kubernetes_name='nvidia-dcgm-exporter',instance=~'.+',gpu=~'<replace>'}"
gpu_infos_query_free = "DCGM_FI_DEV_FB_FREE{app='nvidia-dcgm-exporter'}"
gpu_infos_query_used = "DCGM_FI_DEV_FB_USED{app='nvidia-dcgm-exporter'}"

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
    free_request_url = f"{prometheus_url}{gpu_infos_query_free}"
    used_request_url = f"{prometheus_url}{gpu_infos_query_used}"
    try:
        free_response = requests.get(free_request_url, timeout=1)
        free_result = free_response.json()
        used_response = requests.get(used_request_url, timeout=1)
        used_result = used_response.json()
    except:
        logger.error(f"+++++++++ Could not fetch node-info for GPUs - requests failed")
        return []

    if "status" in free_result and free_result["status"] == "success" and "status" in used_result and used_result["status"] == "success":
        free_gpu_infos = free_result["data"]["result"]
        used_gpu_infos = used_result["data"]["result"]

        gpu_list = []
        for i in range(0, len(free_gpu_infos)):
            free_gpu_info = free_gpu_infos[i]
            used_gpu_info = used_gpu_infos[i]

            node = free_gpu_info["metric"]["Hostname"]
            gpu_id = free_gpu_info["metric"]["gpu"]
            pool_id = f"NODE_GPU_{gpu_id}_MEM"
            gpu_name = free_gpu_info["metric"]["modelName"]
            free = int(free_gpu_info["value"][1])
            used = int(used_gpu_info["value"][1])
            capacity = free + used

            gpu_list.append({
                "node": node,
                "gpu_id": gpu_id,
                "pool_id": pool_id,
                "gpu_name": gpu_name,
                "used": used,
                "free": free,
                "capacity": capacity,
                "queued_count": 0,
                "queued_mb": 0
            })

        gpu_list = sorted(gpu_list, key=lambda d: d['capacity'])
        return gpu_list

    else:
        logger.error(f"+++++++++ Could not fetch node-info for GPUs - success != true")
        return []


def get_node_memory(logger=None):
    node_memory, success = get_node_info(query=memory_query)
    if not success:
        if logger != None:
            logger.error(f"+++++++++ Could not fetch node-info: get_node_memory")
        return None

    return node_memory


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
            logger.error(f"+++++++++ Could not fetch node-info: get_node_cpu_util_percent")
        return None

    return cpu_util_per
