from airflow.models import Pool as pool_api
from kaapana.kubetools.prometheus_query import get_node_memory, get_node_mem_percent, get_node_cpu, get_node_cpu_util_percent, get_node_gpu_infos
import os

print("__init__ kaapana plugin")
pools = pool_api.get_pools()

pools_dict = {}
for pool in pools:
    pools_dict[pool.pool] = pool.slots

if "NODE_RAM" not in pools_dict:
    print("Create Memory Pool ...")
    node_memory = get_node_memory()
    print(f"{node_memory=}")
    pool_api.create_or_update_pool(
        name="NODE_RAM",
        slots=node_memory,
        description="Memory of the node in MB"
    )

if "NODE_CPU_CORES" not in pools_dict:
    print("Create CPU Pool ...")
    node_cpu = get_node_cpu()
    print(f"{node_cpu=}")
    node_gpu_info = get_node_gpu_infos
    print(f"{get_node_gpu_infos=}")
    pool_api.create_or_update_pool(
        name="NODE_CPU_CORES",
        slots=node_cpu,
        description="Count of CPU-cores of the node"
    )

if "NODE_GPU_COUNT" not in pools_dict or (os.getenv("GPU_SUPPORT","false").lower() == "true" and pools_dict["NODE_GPU_COUNT"] == 0):
    print("Create GPU Pool ...")
    node_gpu_infos = get_node_gpu_infos()
    print(f"{node_gpu_infos=}")
    pool_api.create_or_update_pool(
        name="NODE_GPU_COUNT",
        slots=len(node_gpu_infos),
        description="Count of GPUs of the node"
    )

    for gpu_info in node_gpu_infos:
        node = gpu_info["metric"]["Hostname"]
        gpu_id = gpu_info["metric"]["gpu"]
        gpu_name = gpu_info["metric"]["modelName"]
        capacity = int(gpu_info["value"][1])
        pool_api.create_or_update_pool(
            name=f"NODE_GPU_{gpu_id}_MEM",
            slots=capacity,
            description=f"{gpu_name} capacity in MB"
        )