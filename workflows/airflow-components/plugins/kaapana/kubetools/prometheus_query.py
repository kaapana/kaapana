from pprint import pprint
import requests
import time
import json

prometheus_url = "http://prometheus-service.monitoring.svc:9090/prometheus/api/v1/query?query="


memory_query = "floor(sum(machine_memory_bytes)/1048576)"
mem_util_per_query = "sum (container_memory_working_set_bytes{id=\"/\"}) / sum (machine_memory_bytes) * 100"

cpu_core_query = "machine_cpu_cores"
cpu_util_per_query = "sum (rate (container_cpu_usage_seconds_total{id=\"/\"}[1m])) / sum (machine_cpu_cores) * 100"
cpu_util_cores_used_query = "sum(rate (container_cpu_usage_seconds_total{id=\"/\"}[1m]))"


gpu_count_query = "count(DCGM_FI_DEV_POWER_USAGE{kubernetes_name='nvidia-dcgm-exporter'})"
gpu_mem_used_device_query = "DCGM_FI_DEV_FB_USED{kubernetes_name='nvidia-dcgm-exporter',instance=~'.+',gpu=~'<replace>'}"
gpu_mem_available_device_query = "DCGM_FI_DEV_FB_FREE{kubernetes_name='nvidia-dcgm-exporter',instance=~'.+',gpu=~'<replace>'}"
gpu_infos_query="DCGM_FI_DEV_FB_FREE{app='nvidia-dcgm-exporter'}"

def get_node_info(query):
    tries = 0
    max_tries = 4
    result_value = None
    success = True
    while result_value == None and tries < max_tries:
        request_url = "{}{}".format(prometheus_url, query)
        response = requests.get(request_url)
        result = response.json()["data"]["result"]
        if isinstance(result, list) and len(result) > 0:
            result_value = int(float(response.json()["data"]["result"][0]["value"][1]))
        elif "nvidia" in query:
            result_value = 0
        else:
            time.sleep(1)
            tries += 1
    if tries >= max_tries:
        print(f"+++++++++ Could not fetch node-info for query: {query}")
        success = False

    if not isinstance(result_value, int):
        result_value = 0

    return result_value, success


def get_node_memory(logger=None):
    node_memory, success = get_node_info(query=memory_query)
    if not success and logger != None: 
        logger.error(f"+++++++++ Could not fetch node-info: get_node_memory")
        return None

    return node_memory

def get_node_mem_percent(logger=None):
    mem_percent, success = get_node_info(query=mem_util_per_query)
    if not success and logger != None: 
        logger.error(f"+++++++++ Could not fetch node-info: get_node_mem_percent")
        return None

    return mem_percent

def get_node_cpu(logger=None):
    node_cpu, success = get_node_info(query=cpu_core_query)
    if not success and logger != None: 
        logger.error(f"+++++++++ Could not fetch node-info: get_node_cpu")
    return node_cpu

def get_node_cpu_util_percent(logger=None):
    cpu_util_per, success = get_node_info(query=cpu_util_per_query)
    if not success and logger != None: 
        logger.error(f"+++++++++ Could not fetch node-info: get_node_cpu_util_percent")
        return None

    return cpu_util_per


def get_node_gpu_infos(logger=None):
    gpu_infos = []
    request_url = f"{prometheus_url}{gpu_infos_query}"
    response = requests.get(request_url)
    result = response.json()
    if "status" in result and result["status"] == "success":
        gpu_infos = result["data"]["result"]

    elif logger != None:
        logger.error(f"+++++++++ Could not fetch node-info for GPUs")

    return gpu_infos
