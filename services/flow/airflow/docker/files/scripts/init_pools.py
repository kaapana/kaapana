from airflow.models import Pool as pool_api
from kaapana.kubetools.util_helper import NodeUtil

import requests
import time
from uuid import getnode

# Will show up under airflow.hooks.test_plugin.PluginHook

cpu_core_query = "sum(machine_cpu_cores)"
memory_query = "floor(sum(machine_memory_bytes)/1048576)"
gpu_query = "sum(nvidia_gpu_num_devices)"
gpu_mem_used_query = "ceil(sum(nvidia_gpu_memory_used_bytes)/1048576)"
gpu_mem_available_query = "floor(sum(nvidia_gpu_memory_total_bytes)/1048576)"
prometheus_url = "http://prometheus-service.monitoring.svc:9090/prometheus/api/v1/query?query="

def get_node_info(query):
    max_tries = 5
    tries = 0
    result_value = None

    while result_value == None and tries < max_tries:
        request_url = "{}{}".format(prometheus_url, query)
        response = requests.get(request_url,timeout=2)
        result = response.json()["data"]["result"]
        if isinstance(result, list) and len(result) > 0:
            result_value = int(response.json()["data"]["result"][0]["value"][1])
            print("Got result for query: {}: {} - ok!".format(query,result_value))
        else:
            if "nvidia" in query:
                tries += 4    
            print("Could not retrieve node-info -> waiting 2s ...")
            time.sleep(2)
            tries += 1
    
    if tries >= max_tries:
        if "nvidia" in query:
            print("No GPU found... - OK!")
            result_value = 0
        else:
            print("+++++++++++++++++++++++++++++++++++++++++ Could not fetch node-info!")
            exit(1)

    return result_value


def init_pools():

    pools = pool_api.get_pools()
    pools = [i.pool for i in pools]

    if "MEMORY" not in pools:
        print()
        print("Get node resources...")
        print()
        node_memory = get_node_info(query=memory_query)
        node_cpu = get_node_info(query=cpu_core_query)
        node_gpu_mem = get_node_info(query=gpu_mem_available_query)
        node_gpu_count = get_node_info(query=gpu_query)
        try:
            print("+++++++++++++++++++++++++++++++++++++++++++++ CREATING MEMORY POOL")
            pool_api.create_or_update_pool(
                name="MEMORY",
                slots=abs(node_memory - 10000),
                description="Memory of the node in MB"
            )
            # Variable.set("mem_alloc", NodeUtil.mem_alloc)

            print("+++++++++++++++++++++++++++++++++++++++++++++ CREATING CPU POOL")
            pool_api.create_or_update_pool(
                name="CPU",
                slots=node_cpu,
                description="Count of CPU-cores of the node"
            )
            # Variable.set("cpu_alloc", NodeUtil.cpu_alloc)

            print("+++++++++++++++++++++++++++++++++++++++++++++ CREATING GPU POOL")
            pool_api.create_or_update_pool(
                name="GPU_MEM",
                slots=node_gpu_mem,
                description="Memory of all GPUs of the node in MB"
            )
            pool_api.create_or_update_pool(
                name="GPU_COUNT",
                slots=node_gpu_count,
                description="Count of GPUs of the node"
            )
            # Variable.set("gpu_alloc", NodeUtil.gpu_alloc)
            # Variable.set("gpu_count", NodeUtil.gpu_count)

        except Exception as e:
            print("++++++++++++++++++++++++++++++++++++++ Error @ creating pools!")
            print(e)
            exit(1)

init_pools()
