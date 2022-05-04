import kubernetes as k8s
from datetime import datetime
from threading import Thread
from pint import UnitRegistry
from collections import defaultdict
import os
from airflow.models import Variable
import logging

class UtilService(Thread):
    stopFlag = None
    query_delay = None

    self_object = None

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

    def __init__(self, event):
        Thread.__init__(self)
        self.stopped = event

        k8s.config.load_incluster_config()
        UtilService.core_v1 = k8s.client.CoreV1Api()
        UtilService.ureg = UnitRegistry()
        units_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'kubernetes_units.txt')

        assert os.path.isfile(units_file_path)
        UtilService.ureg.load_definitions(units_file_path)
        UtilService.Q_ = UtilService.ureg.Quantity

        # UtilService.get_utilization()

    def run(self):
        while not self.stopped.wait(UtilService.query_delay):
            UtilService.get_utilization()


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

            if Variable.get("cluster_requested_memory_mb") !=  UtilService.mem_req or \
                Variable.get("cluster_available_memory_mb") !=  UtilService.mem_alloc or \
                Variable.get("cluster_available_cpu") !=  UtilService.cpu_alloc or \
                Variable.get("cluster_gpu_count") !=  UtilService.gpu_dev_count:

                Variable.update("cluster_requested_memory_mb", UtilService.mem_req)
                Variable.update("cluster_available_memory_mb", UtilService.mem_alloc)
                Variable.update("cluster_available_cpu", UtilService.cpu_alloc)
                Variable.update("cluster_gpu_count", UtilService.gpu_dev_count)
                Variable.update("enable_pool_manager", "True")
                
            # UtilService.gpu_memory_available = None if (UtilService.gpu_mem_alloc is None or UtilService.gpu_mem_used is None) else (UtilService.gpu_mem_alloc - UtilService.gpu_mem_used)

            logger.error("#####################################")
            logger.error("#####################################")
            logger.error("")
            logger.error(f"# {UtilService.cpu_alloc=}")
            logger.error(f"# {UtilService.cpu_req=}")
            logger.error(f"# {UtilService.cpu_lmt=}")
            logger.error(f"# {UtilService.cpu_req_per=}")
            logger.error(f"# {UtilService.cpu_lmt_per=}")
            logger.error(f"# {UtilService.mem_alloc=}")
            logger.error(f"# {UtilService.mem_req=}")
            logger.error(f"# {UtilService.mem_lmt=}")
            logger.error(f"# {UtilService.mem_req_per=}")
            logger.error(f"# {UtilService.mem_lmt_per=}")
            logger.error(f"# {UtilService.gpu_dev_count=}")
            logger.error(f"# {UtilService.memory_pressure=}")
            logger.error(f"# {UtilService.disk_pressure=}")
            logger.error(f"# {UtilService.pid_pressure=}")
            logger.error(f"# {UtilService.cpu_available_req=}")
            logger.error(f"# {UtilService.cpu_available_limit=}")
            logger.error(f"# {UtilService.memory_available_req=}")
            logger.error(f"# {UtilService.memory_available_limit=}")
            logger.error("")
            logger.error("#####################################")
            logger.error("#####################################")

            # return True

        except Exception as e:
            logger.error("+++++++++++++++++++++++++++++++++++++++++ COULD NOT FETCH NODES!")
            logger.error(e)
            return False
