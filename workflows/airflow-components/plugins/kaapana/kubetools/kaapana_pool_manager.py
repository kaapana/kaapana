from requests import session
from airflow.models import Pool as pool_api
from airflow.models import Variable
from kaapana.kubetools.prometheus_query import get_node_memory, get_node_cpu, get_node_gpu_infos
from threading import Thread
import os
import logging
from airflow.settings import Session


class KaapanaPoolManager(Thread):
    pools_dict = None
    stopFlag = None
    short_delay = 10
    query_delay = None
    gpu_support = None

    cpu_pool_set = False
    ram_pool_set = False
    gpu_pool_set = False

    self_object = None

    def __init__(self, event):
        Thread.__init__(self)
        self.stopped = event
        KaapanaPoolManager.session = Session()
        KaapanaPoolManager.gpu_support = os.getenv("GPU_SUPPORT", "false").lower() == "true"
        if KaapanaPoolManager.gpu_support:
            KaapanaPoolManager.query_delay = KaapanaPoolManager.short_delay

        KaapanaPoolManager.check_pools(force=True)

    def run(self):
        while not self.stopped.wait(KaapanaPoolManager.query_delay):
            KaapanaPoolManager.check_pools()

    @staticmethod
    def check_pools(logger=logging, force=False):
        logger.error(f"KaapanaPoolManager -> check_pools!")

        KaapanaPoolManager.pools_dict = pool_api.slots_stats()
        pool_id = "NODE_RAM"
        if pool_id not in KaapanaPoolManager.pools_dict or force:
            cluster_requested_memory_mb = int(Variable.get("cluster_requested_memory_mb"))
            cluster_available_memory_mb = int(Variable.get("cluster_available_memory_mb"))

            # node_memory = get_node_memory(logger=logger)
            if cluster_available_memory_mb == None or cluster_available_memory_mb == 0:
                logger.error(f"Adjust pool {pool_id}: could not fetch node info -> skipping")
            else:
                cluster_available_memory_mb = abs(cluster_available_memory_mb - cluster_requested_memory_mb)

                print(f"{cluster_requested_memory_mb=}")
                print(f"Adjust pool {pool_id}: {cluster_available_memory_mb}")
                pool_api.create_or_update_pool(
                    name=pool_id,
                    slots=cluster_available_memory_mb,
                    description="Memory of the node in MB"
                )
                KaapanaPoolManager.ram_pool_set = True
        else:
            KaapanaPoolManager.ram_pool_set = True

        pool_id = "NODE_CPU_CORES"
        if pool_id not in KaapanaPoolManager.pools_dict or force:
            cluster_available_cpu = int(Variable.get("cluster_available_cpu"))
            # node_cpu = get_node_cpu(logger=logger)
            if cluster_available_cpu == None or cluster_available_cpu == 0:
                logger.error(f"Adjust pool {pool_id}: could not fetch node info -> skipping")
            else:
                logger.info(f"Adjust pool {pool_id}: {cluster_available_cpu}")
                pool_api.create_or_update_pool(
                    name=pool_id,
                    slots=cluster_available_cpu,
                    description="Count of CPU-cores of the node"
                )
                KaapanaPoolManager.cpu_pool_set = True
        else:
            KaapanaPoolManager.cpu_pool_set = True

        pool_id = "NODE_GPU_COUNT"
        if pool_id not in KaapanaPoolManager.pools_dict or (KaapanaPoolManager.gpu_support and KaapanaPoolManager.pools_dict["NODE_GPU_COUNT"]["total"] == 0) or force:
            cluster_gpu_count = int(Variable.get("cluster_gpu_count"))
            if cluster_gpu_count == None or (cluster_gpu_count == 0 and KaapanaPoolManager.gpu_support):
                logger.error(f"Adjust pool {pool_id}: could not fetch node info -> skipping")
            else:
                logger.info(f"Adjust pool {pool_id}: {cluster_gpu_count}")
                pool_api.create_or_update_pool(
                    name=pool_id,
                    slots=cluster_gpu_count,
                    description="Count of GPUs of the node"
                )

                if cluster_gpu_count > 0:
                    logger.error("Getting node GPU info ...")

                    node_gpu_list = get_node_gpu_infos(logger=logger)
                    for gpu_info in node_gpu_list:
                        node = gpu_info["node"]
                        gpu_id = gpu_info["gpu_id"]
                        pool_id = gpu_info["pool_id"]
                        gpu_name = gpu_info["gpu_name"]
                        capacity = gpu_info["capacity"]
                        logger.info(f"Adjust pool {pool_id}: {capacity}")
                        pool_api.create_or_update_pool(
                            name=pool_id,
                            slots=capacity,
                            description=f"{gpu_name} capacity in MB"
                        )
                        KaapanaPoolManager.gpu_pool_set = True
                    else:
                        KaapanaPoolManager.gpu_pool_set = True
        else:
            KaapanaPoolManager.gpu_pool_set = True

        if KaapanaPoolManager.cpu_pool_set and KaapanaPoolManager.ram_pool_set:
            if KaapanaPoolManager.gpu_support and not KaapanaPoolManager.gpu_pool_set:
                logger.info(f"GPU activated but not set yet -> continue pool monitoring.")
                return
            else:
                logger.info(f"All pools set -> deactivating KaapanaPoolManager ...")
                Variable.update(key="enable_pool_manager", value="False", session=KaapanaPoolManager.session)
                KaapanaPoolManager.stopFlag.set()
