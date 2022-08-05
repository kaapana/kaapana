import json
import kubernetes as k8s
from datetime import datetime
from pint import UnitRegistry
from collections import defaultdict
import os
import logging
from kaapana.kubetools.prometheus_query import get_node_gpu_infos
from subprocess import PIPE, run, Popen
# from subprocess import STDOUT, check_output
from kubernetes.client.models.v1_container_image import V1ContainerImage

gpu_support = True if os.getenv('GPU_SUPPORT', "False").lower() == "true" else False


class UtilService():
    query_delay = None
    api_client = None

    ureg = None
    last_update = None

    cpu_alloc = None
    cpu_req = None
    cpu_lmt = None
    cpu_req_per = None
    cpu_lmt_per = None
    cpu_percent = None
    max_util_cpu = None

    gpu_alloc = None
    gpu_used = None
    gpu_dev_count = None

    mem_alloc = None
    mem_req = None
    mem_lmt = None
    mem_req_per = None
    mem_lmt_per = None
    mem_percent = None
    max_util_ram = None

    cpu_available_req = None
    cpu_available_limit = None
    memory_available_req = None
    memory_available_limit = None
    gpu_memory_available = None

    pool_mem = None
    pool_cpu = None
    pool_gpu_count = None

    node_gpu_list = []
    node_gpu_queued_dict = {}

    @staticmethod
    def create_pool(pool_name, pool_slots, pool_description, logger=logging):
        command = ["airflow", "pools", "set", str(pool_name), str(pool_slots), str(pool_description)]
        logger.error(f"Creating pool {pool_name}: {pool_slots} - {pool_description}")
        output = Popen(command)

    @staticmethod
    def init_util_service():
        def names(self, names):
            self._names = names
        V1ContainerImage.names = V1ContainerImage.names.setter(names)
        k8s.config.load_incluster_config()
        UtilService.core_v1 = k8s.client.CoreV1Api()
        UtilService.ureg = UnitRegistry()
        units_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'kubernetes_units.txt')

        assert os.path.isfile(units_file_path)
        UtilService.ureg.load_definitions(units_file_path)
        UtilService.Q_ = UtilService.ureg.Quantity

    @staticmethod
    def get_utilization(logger=logging):
        logger.error("UtilService -> get_utilization")

        data = {}
        UtilService.last_update = datetime.now()

        try:
            for node in UtilService.core_v1.list_node().items:
                stats = {}
                node_name = node.metadata.name
                capacity = node.status.capacity
                allocatable = node.status.allocatable
                conditions = node.status.conditions
                stats["memory_pressure"] = False
                stats["disk_pressure"] = False
                stats["pid_pressure"] = False
                for condition in conditions:
                    if condition.type == "MemoryPressure":
                        stats["memory_pressure"] = True if condition.status == "True" else False
                    elif condition.type == "DiskPressure":
                        stats["disk_pressure"] = True if condition.status == "True" else False
                    elif condition.type == "PIDPressure":
                        stats["pid_pressure"] = True if condition.status == "True" else False

                max_pods = int(int(allocatable["pods"]) * 1.5)
                field_selector = ("status.phase!=Succeeded,status.phase!=Failed," + "spec.nodeName=" + node_name)

                stats["cpu_alloc"] = UtilService.Q_(allocatable["cpu"])
                stats["mem_alloc"] = UtilService.Q_(allocatable["memory"])
                stats["gpu_dev_count"] = UtilService.Q_(capacity["nvidia.com/gpu"] if "nvidia.com/gpu" in capacity else 0)
                stats["gpu_dev_free"] = UtilService.Q_(allocatable["nvidia.com/gpu"] if "nvidia.com/gpu" in allocatable else 0)

                pods = UtilService.core_v1.list_pod_for_all_namespaces(limit=max_pods, field_selector=field_selector).items
                # compute the allocated resources
                cpureqs, cpulmts, memreqs, memlmts = [], [], [], []
                for pod in pods:
                    for container in pod.spec.containers:
                        res = container.resources
                        reqs = defaultdict(lambda: 0, res.requests or {})
                        lmts = defaultdict(lambda: 0, res.limits or {})
                        cpureqs.append(UtilService.Q_(reqs["cpu"]))
                        memreqs.append(UtilService.Q_(reqs["memory"]))
                        cpulmts.append(UtilService.Q_(lmts["cpu"]))
                        memlmts.append(UtilService.Q_(lmts["memory"]))

                stats["cpu_req"] = sum(cpureqs)
                stats["cpu_lmt"] = sum(cpulmts)
                stats["cpu_req_per"] = (stats["cpu_req"] / stats["cpu_alloc"] * 100)
                stats["cpu_lmt_per"] = (stats["cpu_lmt"] / stats["cpu_alloc"] * 100)
                stats["mem_req"] = sum(memreqs)
                stats["mem_lmt"] = sum(memlmts)
                stats["mem_req_per"] = (stats["mem_req"] / stats["mem_alloc"] * 100)
                stats["mem_lmt_per"] = (stats["mem_lmt"] / stats["mem_alloc"] * 100)
                data[node_name] = stats

            node_info = next(iter(data.values()))
            UtilService.cpu_alloc = node_info["cpu_alloc"].to_base_units().magnitude * 1000
            UtilService.cpu_req = node_info["cpu_req"].to_base_units().magnitude * 1000
            UtilService.cpu_lmt = node_info["cpu_lmt"].to_base_units().magnitude * 1000
            UtilService.cpu_req_per = int(node_info["cpu_req_per"].to_base_units().magnitude * 1000)
            UtilService.cpu_lmt_per = int(node_info["cpu_lmt_per"].to_base_units().magnitude * 1000)
            UtilService.mem_alloc = int(node_info["mem_alloc"].to_base_units().magnitude // 1024 // 1024)
            UtilService.mem_req = int(node_info["mem_req"].to_base_units().magnitude // 1024 // 1024)
            UtilService.mem_lmt = int(node_info["mem_lmt"].to_base_units().magnitude // 1024 // 1024)
            UtilService.mem_req_per = int(node_info["mem_req_per"].to_base_units().magnitude)
            UtilService.mem_lmt_per = int(node_info["mem_lmt_per"].to_base_units().magnitude)
            UtilService.gpu_dev_count = int(node_info["gpu_dev_count"])
            UtilService.gpu_dev_free = int(node_info["gpu_dev_free"])
            UtilService.memory_pressure = node_info["memory_pressure"]
            UtilService.disk_pressure = node_info["disk_pressure"]
            UtilService.pid_pressure = node_info["pid_pressure"]

            UtilService.cpu_available_req = UtilService.cpu_alloc - UtilService.cpu_req
            UtilService.cpu_available_limit = UtilService.cpu_alloc - UtilService.cpu_lmt
            UtilService.memory_available_req = abs(UtilService.mem_alloc - UtilService.mem_req)
            UtilService.memory_available_limit = abs(UtilService.mem_alloc - UtilService.mem_lmt)

            pool_id = "NODE_GPU_COUNT"
            if UtilService.pool_gpu_count == None or UtilService.pool_gpu_count != UtilService.gpu_dev_count or UtilService.pool_gpu_count == 0 and gpu_support:
                UtilService.create_pool(
                    pool_name=pool_id,
                    pool_slots=UtilService.gpu_dev_count,
                    pool_description="Pool for the GPU device count",
                    logger=logger
                )
                UtilService.pool_gpu_count = UtilService.gpu_dev_count

                if UtilService.gpu_dev_count > 0:
                    UtilService.node_gpu_list = get_node_gpu_infos(logger=logger) if UtilService.gpu_dev_count > 0 else []
                    if len(UtilService.node_gpu_list) == 0:
                        UtilService.pool_gpu_count = None
                    else:
                        for gpu_info in UtilService.node_gpu_list:
                            node = gpu_info["node"]
                            gpu_id = gpu_info["gpu_id"]
                            pool_id = gpu_info["pool_id"]
                            gpu_name = gpu_info["gpu_name"]
                            capacity = gpu_info["capacity"]
                            logger.info(f"Adjust pool {pool_id}: {capacity}")

                            if pool_id not in UtilService.node_gpu_queued_dict:
                                UtilService.node_gpu_queued_dict[pool_id] = 0

                            create_pool = False
                            UtilService.create_pool(
                                pool_name=pool_id,
                                pool_slots=capacity,
                                pool_description=f"{gpu_name} capacity in MB",
                                logger=logger
                            )
            else:
                UtilService.pool_gpu_count = UtilService.gpu_dev_count
                UtilService.node_gpu_list = get_node_gpu_infos(logger=logger) if UtilService.gpu_dev_count > 0 else []

            pool_id = "NODE_RAM"
            processing_memory_node = abs(UtilService.mem_alloc - UtilService.mem_req)
            if UtilService.pool_mem == None:
                # if UtilService.pool_mem == None or UtilService.pool_mem != processing_memory_node:
                UtilService.create_pool(
                    pool_name=pool_id,
                    pool_slots=processing_memory_node,
                    pool_description="Pool for the available nodes RAM memory in MB",
                    logger=logger
                )
                UtilService.pool_mem = processing_memory_node

            pool_id = "NODE_CPU_CORES"
            if UtilService.pool_cpu == None or UtilService.pool_cpu != UtilService.cpu_alloc:
                UtilService.create_pool(
                    pool_name=pool_id,
                    pool_slots=UtilService.cpu_alloc,
                    pool_description="Pool for the available CPU cores",
                    logger=logger
                )
                UtilService.pool_cpu = UtilService.cpu_alloc

            logger.debug("#####################################")
            logger.debug("#####################################")
            logger.debug("")
            logger.debug(f"# {UtilService.cpu_alloc=}")
            logger.debug(f"# {UtilService.cpu_req=}")
            logger.debug(f"# {UtilService.cpu_lmt=}")
            logger.debug(f"# {UtilService.cpu_req_per=}")
            logger.debug(f"# {UtilService.cpu_lmt_per=}")
            logger.debug(f"# {UtilService.mem_alloc=}")
            logger.debug(f"# {UtilService.mem_req=}")
            logger.debug(f"# {UtilService.mem_lmt=}")
            logger.debug(f"# {UtilService.mem_req_per=}")
            logger.debug(f"# {UtilService.mem_lmt_per=}")
            logger.debug(f"# {UtilService.gpu_dev_count=}")
            logger.debug(f"# {UtilService.memory_pressure=}")
            logger.debug(f"# {UtilService.disk_pressure=}")
            logger.debug(f"# {UtilService.pid_pressure=}")
            logger.debug(f"# {UtilService.cpu_available_req=}")
            logger.debug(f"# {UtilService.cpu_available_limit=}")
            logger.debug(f"# {UtilService.memory_available_req=}")
            logger.debug(f"# {UtilService.memory_available_limit=}")
            logger.debug("")
            logger.debug("#####################################")
            logger.debug("#####################################")

        except Exception as e:
            logger.error("+++++++++++++++++++++++++++++++++++++++++ COULD NOT FETCH NODES!")
            logger.error(e)
            return False

    @staticmethod
    def check_operator_scheduling(task_instance, logger=logging):
        logger.info(f"UtilService: check_operator_scheduling {task_instance.task_id=}")
        job_scheduler_delay = 10

        if "enable_job_scheduler" in task_instance.executor_config and not task_instance.executor_config["enable_job_scheduler"]:
            logger.warning(f"UtilService: enable_job_scheduler disabled!")
            return True, task_instance.pool, task_instance.pool_slots

        logging.info(f"{UtilService.last_update=}")
        if UtilService.last_update == None:
            UtilService.init_util_service()
            UtilService.get_utilization(logger=logger)
        elif (datetime.now() - UtilService.last_update).total_seconds() > job_scheduler_delay:
            UtilService.get_utilization(logger=logger)

        if "gpu_mem_mb" in task_instance.executor_config and task_instance.executor_config["gpu_mem_mb"] != None and task_instance.executor_config["gpu_mem_mb"] > 0:
            if "gpu" in str(task_instance.pool).lower():
                logger.info(f"GPU pool already set!")
            else:
                gpu_mem_mb = task_instance.executor_config["gpu_mem_mb"]
                if len(UtilService.node_gpu_queued_dict) > 0:
                    for i in range(0, len(UtilService.node_gpu_list)):  # setting cached execution counts
                        gpu_info = UtilService.node_gpu_list[i]
                        pool_id = gpu_info["pool_id"]
                        if pool_id in UtilService.node_gpu_queued_dict:
                            if UtilService.node_gpu_queued_dict[pool_id] > 10:
                                for key,value in UtilService.node_gpu_queued_dict.items():
                                    UtilService.node_gpu_queued_dict[key] = 0

                        UtilService.node_gpu_list[i]["queued_count"] = UtilService.node_gpu_queued_dict[pool_id]

                logger.info(f"GPU status:")
                UtilService.node_gpu_list = sorted(UtilService.node_gpu_list, key=lambda d: d['queued_count'])
                for gpu_info in UtilService.node_gpu_list:
                    logger.info(json.dumps(gpu_info, indent=4))

                for i in range(0, len(UtilService.node_gpu_list)):  # Check if queued_left has enough ram
                    gpu_info = UtilService.node_gpu_list[i]
                    pool_id = gpu_info["pool_id"]
                    capacity = gpu_info["capacity"]
                    free = gpu_info["free"]
                    queued_count = gpu_info["queued_count"]
                    queued_mb = gpu_info["queued_mb"]
                    queued_left = abs(capacity - queued_mb)

                    if capacity >= gpu_mem_mb and free >= gpu_mem_mb and queued_left >= gpu_mem_mb:
                        UtilService.node_gpu_queued_dict[pool_id] += 1
                        UtilService.node_gpu_list[i]["queued_count"] += 1
                        UtilService.node_gpu_list[i]["queued_mb"] += gpu_mem_mb
                        return False, pool_id, gpu_mem_mb

                for i in range(0, len(UtilService.node_gpu_list)):  # Check for capacity
                    gpu_info = UtilService.node_gpu_list[i]
                    pool_id = gpu_info["pool_id"]
                    capacity = gpu_info["capacity"]
                    free = gpu_info["free"]

                    logger.error(json.dumps(gpu_info, indent=4))
                    if capacity >= gpu_mem_mb:
                        UtilService.node_gpu_queued_dict[pool_id] += 1
                        UtilService.node_gpu_list[i]["queued_count"] += 1
                        UtilService.node_gpu_list[i]["queued_mb"] += gpu_mem_mb
                        return False, pool_id, gpu_mem_mb

                logger.error(f"No GPU for the TI found! -> Not scheduling !")
                if not gpu_support:
                    pool_id = "NODE_GPU_COUNT"
                    return False, pool_id, 1
                else:
                    return False, task_instance.pool, task_instance.pool_slots

        if UtilService.memory_pressure:
            logger.error("UtilService.memory_pressure == TRUE -> not scheduling!")
            return False, task_instance.pool, task_instance.pool_slots

        if UtilService.disk_pressure:
            logger.error("UtilService.disk_pressure == TRUE -> not scheduling!")
            return False, task_instance.pool, task_instance.pool_slots

        if UtilService.pid_pressure:
            logger.error("UtilService.pid_pressure == TRUE -> not scheduling!")
            return False, task_instance.pool, task_instance.pool_slots

        if "cpu_millicores" in task_instance.executor_config and task_instance.executor_config["cpu_millicores"] != None:
            # TODO
            pass

        if "ram_mem_mb" in task_instance.executor_config and task_instance.executor_config["ram_mem_mb"] != None:
            if task_instance.executor_config["ram_mem_mb"] > UtilService.memory_available_req:
                logger.error("TI ram_mem_mb > UtilService.memory_available_req -> not scheduling!")
                return False, task_instance.pool, task_instance.pool_slots

        logging.info("ok")
        return True, task_instance.pool, task_instance.pool_slots
