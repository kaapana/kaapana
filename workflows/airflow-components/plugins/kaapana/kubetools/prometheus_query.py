from pprint import pprint
import requests
import time

mem_util_per_query = "sum (container_memory_working_set_bytes{id=\"/\"}) / sum (machine_memory_bytes) * 100"
cpu_core_query = "sum(machine_cpu_cores)"
cpu_util_per_query = "sum (rate (container_cpu_usage_seconds_total{id=\"/\"}[1m])) / sum (machine_cpu_cores) * 100"
cpu_util_cores_used_query = "sum(rate (container_cpu_usage_seconds_total{id=\"/\"}[1m]))"
memory_query = "floor(sum(machine_memory_bytes)/1048576)"
gpu_query = "sum(nvidia_gpu_num_devices)"
gpu_mem_used_query = "ceil(sum(nvidia_gpu_memory_used_bytes)/1048576)"
gpu_mem_available_query = "floor(sum(nvidia_gpu_memory_total_bytes)/1048576)"
gpu_mem_available_device = "nvidia_gpu_memory_total_bytes{minor_number='<replace>'}/1048576"
prometheus_url = "http://prometheus-service.monitoring.svc:9090/prometheus/api/v1/query?query="

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
    node_gpu_count, success = get_node_info(query=gpu_query)
    for i in range(0, node_gpu_count):
        tries = 0
        max_tries = 4
        success = False
        while not success and tries < max_tries:
            request_url = f"{prometheus_url}{gpu_mem_available_device.replace('<replace>', str(i))}"
            response = requests.get(request_url)
            result = response.json()
            if "data" in result and "result" in result["data"] and isinstance(result["data"]["result"], list) and len(result["data"]["result"]) > 0:
                result = result["data"]["result"][0]
                name = result["metric"]["name"]
                mem_capacity = result["value"][1]
                success = True
            else:
                time.sleep(1)
                tries += 1
        if success:
            gpu_info = {
                "id": i,
                "name": name,
                "mem_capacity": int(float(mem_capacity)),
            }
            gpu_infos.append(gpu_info)
        elif logger != None:
            logger.error(f"+++++++++ Could not fetch node-info for get_node_gpu_infos: {i}")
    return gpu_infos
