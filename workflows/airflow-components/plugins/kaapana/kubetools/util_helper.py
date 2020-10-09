import kubernetes as k8s
from pint import UnitRegistry
from collections import defaultdict
import requests
from datetime import timedelta, datetime
import time
import os

from airflow.models import Variable
from kubernetes.client.models.v1_container_image import V1ContainerImage


class NodeUtil():
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
    gpu_count = None

    mem_alloc = None
    mem_req = None
    mem_lmt = None
    mem_req_per = None
    mem_lmt_per = None
    mem_percent = None
    max_util_ram = None

    enable = None

    cpu_available_req = None
    cpu_available_limit = None
    memory_available_req = None
    memory_available_limit = None
    gpu_memory_available = None

    mem_util_per_query = "sum (container_memory_working_set_bytes{id=\"/\"}) / sum (machine_memory_bytes) * 100"
    cpu_core_query = "sum(machine_cpu_cores)"
    cpu_util_per_query = "sum (rate (container_cpu_usage_seconds_total{id=\"/\"}[1m])) / sum (machine_cpu_cores) * 100"
    cpu_util_cores_used_query = "sum(rate (container_cpu_usage_seconds_total{id=\"/\"}[1m]))"
    memory_query = "floor(sum(machine_memory_bytes)/1048576)"
    gpu_query = "sum(nvidia_gpu_num_devices)"
    gpu_mem_used_query = "ceil(sum(nvidia_gpu_memory_used_bytes)/1048576)"
    gpu_mem_available_query = "floor(sum(nvidia_gpu_memory_total_bytes)/1048576)"
    prometheus_url = "http://prometheus-service.monitoring.svc:9090/prometheus/api/v1/query?query="

    @staticmethod
    def get_node_info(query, logger=None):
        logger = None

        tries = 0
        result_value = None
        return_code = True

        while result_value == None and tries < 4:
            request_url = "{}{}".format(NodeUtil.prometheus_url, query)
            response = requests.get(request_url)
            result = response.json()["data"]["result"]
            if isinstance(result, list) and len(result) > 0:
                result_value = int(float(response.json()["data"]["result"][0]["value"][1]))
                if logger is not None:
                    logger.warning("Got result for query: {}: {} - ok!".format(query, result_value))
            elif "nvidia" in query:
                if logger is not None:
                    logger.warning("No GPU found... - OK!")
                result_value = 0
            else:
                if logger is not None:
                    logger.error("Could not retrieve node-info -> waiting 1s ...")
                time.sleep(1)
                tries += 1

        if tries >= 10:
            print("+++++++++++++++++++++++++++++++++++++++++ Could not fetch node-info!")
            return_code = False

        if not isinstance(result_value,int):
            result_value = 0
            if logger is not None:
                logger.error("'result_value' was not an integer! -> set to 0 !")

        return result_value, return_code

    @staticmethod
    def get_prom_util():
        node_memory, return_code = NodeUtil.get_node_info(query=NodeUtil.memory_query)
        node_cpu, return_code = NodeUtil.get_node_info(query=NodeUtil.cpu_core_query)
        node_gpu_mem, return_code = NodeUtil.get_node_info(query=NodeUtil.gpu_mem_available_query)
        node_gpu_count, return_code = NodeUtil.get_node_info(query=NodeUtil.gpu_query)

        return node_memory, node_cpu, node_gpu_mem, node_gpu_count

    @staticmethod
    def compute_allocated_resources(logger=None):
        Q_ = NodeUtil.ureg.Quantity
        data = {}
        NodeUtil.last_update = datetime.now()

        try:
            for node in NodeUtil.core_v1.list_node().items:
                stats = {}
                node_name = node.metadata.name
                allocatable = node.status.allocatable
                max_pods = int(int(allocatable["pods"]) * 1.5)
                field_selector = ("status.phase!=Succeeded,status.phase!=Failed,"+"spec.nodeName=" + node_name)

                stats["cpu_alloc"] = Q_(allocatable["cpu"])
                stats["mem_alloc"] = Q_(allocatable["memory"])
                stats["gpu_count"] = Q_(allocatable["nvidia.com/gpu"] if "nvidia.com/gpu" in allocatable else 0)

                pods = NodeUtil.core_v1.list_pod_for_all_namespaces(limit=max_pods, field_selector=field_selector).items

                # compute the allocated resources
                cpureqs, cpulmts, memreqs, memlmts = [], [], [], []
                for pod in pods:
                    for container in pod.spec.containers:
                        res = container.resources
                        reqs = defaultdict(lambda: 0, res.requests or {})
                        lmts = defaultdict(lambda: 0, res.limits or {})
                        cpureqs.append(Q_(reqs["cpu"]))
                        memreqs.append(Q_(reqs["memory"]))
                        cpulmts.append(Q_(lmts["cpu"]))
                        memlmts.append(Q_(lmts["memory"]))

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
            NodeUtil.cpu_alloc = node_info["cpu_alloc"].to_base_units().magnitude * 1000
            NodeUtil.cpu_req = node_info["cpu_req"].to_base_units().magnitude * 1000
            NodeUtil.cpu_lmt = node_info["cpu_lmt"].to_base_units().magnitude * 1000
            NodeUtil.cpu_req_per = int(node_info["cpu_req_per"].to_base_units().magnitude * 1000)
            NodeUtil.cpu_lmt_per = int(node_info["cpu_lmt_per"].to_base_units().magnitude * 1000)
            NodeUtil.mem_alloc = int(node_info["mem_alloc"].to_base_units().magnitude // 1024 // 1024)
            NodeUtil.mem_req = int(node_info["mem_req"].to_base_units().magnitude // 1024 // 1024)
            NodeUtil.mem_lmt = int(node_info["mem_lmt"].to_base_units().magnitude // 1024 // 1024)
            NodeUtil.mem_req_per = int(node_info["mem_req_per"].to_base_units().magnitude)
            NodeUtil.mem_lmt_per = int(node_info["mem_lmt_per"].to_base_units().magnitude)
            NodeUtil.gpu_count = int(node_info["gpu_count"].to_base_units().magnitude)

            if NodeUtil.gpu_count > 0:
                NodeUtil.gpu_alloc, return_code = NodeUtil.get_node_info(query=NodeUtil.gpu_mem_available_query, logger=logger)
                if not return_code and logger is not None:
                    logger.warning("############################################# Could not fetch gpu_alloc utilization from prometheus!!")
                NodeUtil.gpu_used, return_code = NodeUtil.get_node_info(query=NodeUtil.gpu_mem_used_query, logger=logger)
                if not return_code and logger is not None:
                    logger.warning("############################################# Could not fetch gpu_used utilization from prometheus!!")
            else:
                NodeUtil.gpu_alloc = 0
                NodeUtil.gpu_used = 0

            NodeUtil.cpu_available_req = NodeUtil.cpu_alloc - NodeUtil.cpu_req
            NodeUtil.cpu_available_limit = NodeUtil.cpu_alloc - NodeUtil.cpu_lmt
            NodeUtil.memory_available_req = NodeUtil.mem_alloc - NodeUtil.mem_req
            NodeUtil.memory_available_limit = NodeUtil.mem_alloc - NodeUtil.mem_lmt
            NodeUtil.gpu_memory_available = NodeUtil.gpu_alloc - NodeUtil.gpu_used

            Variable.set("RAM-Node", "{}".format(NodeUtil.mem_alloc))
            Variable.set("RAM-Available", "{}".format(NodeUtil.memory_available_req))
            Variable.set("RAM-Requested", "{}".format(NodeUtil.mem_req))
            Variable.set("RAM-Limit", "{}".format(NodeUtil.mem_req))
            Variable.set("CPU", "{}/{}".format(NodeUtil.cpu_lmt, NodeUtil.cpu_alloc))
            Variable.set("CPU-Available", "{}".format(NodeUtil.cpu_available_limit))
            Variable.set("GPU", "{}/{}".format(NodeUtil.gpu_used, NodeUtil.gpu_alloc))
            Variable.set("GPU-Available", "{}".format(NodeUtil.gpu_memory_available))
            Variable.set("UPDATED", datetime.utcnow())

            # Variable.set("cpu_alloc", "{}".format(NodeUtil.cpu_alloc))
            # Variable.set("cpu_req", "{}".format(NodeUtil.cpu_req))
            # Variable.set("cpu_lmt", "{}".format(NodeUtil.cpu_lmt))
            # Variable.set("cpu_req_per", "{}".format(NodeUtil.cpu_req_per))
            # Variable.set("cpu_lmt_per", "{}".format(NodeUtil.cpu_lmt_per))
            # Variable.set("cpu_available_req", "{}".format(NodeUtil.cpu_available_req))
            # Variable.set("cpu_available_limit", "{}".format(NodeUtil.cpu_available_limit))
            # Variable.set("mem_alloc", "{}".format(NodeUtil.mem_alloc))
            # Variable.set("mem_req", "{}".format(NodeUtil.mem_req))
            # Variable.set("mem_lmt", "{}".format(NodeUtil.mem_lmt))
            # Variable.set("mem_req_per", "{}".format(NodeUtil.mem_req_per))
            # Variable.set("mem_lmt_per", "{}".format(NodeUtil.mem_lmt_per))
            # Variable.set("memory_available_req", "{}".format(NodeUtil.memory_available_req))
            # Variable.set("memory_available_limit", "{}".format(NodeUtil.memory_available_limit))
            # Variable.set("gpu_count", "{}".format(NodeUtil.gpu_count))
            # Variable.set("gpu_alloc", "{}".format(NodeUtil.gpu_alloc))
            # Variable.set("gpu_used", "{}".format(NodeUtil.gpu_used))
            # Variable.set("gpu_memory_available", "{}".format(NodeUtil.gpu_memory_available))

            return True

        except Exception as e:
            print("+++++++++++++++++++++++++++++++++++++++++ COULD NOT FETCH NODES!")
            return False

    @staticmethod
    def check_ti_scheduling(ti, logger):
        if NodeUtil.ureg is None:
            logger.warning("Inititalize Util-Helper!")
            NodeUtil.enable = Variable.get(key="util_scheduling", default_var=None)
            if NodeUtil.enable == None:
                Variable.set("util_scheduling", True)
                NodeUtil.enable = 'True'

            logger.warning("-> init UnitRegistry...")
            NodeUtil.ureg = UnitRegistry()
            units_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'kubernetes_units.txt')
            if not os.path.isfile(units_file_path):
                logger.warning("Could not find kubernetes_units.txt @  {} !".format(units_file_path))
                logger.warning("abort.")
                exit(1)
            else:
                NodeUtil.ureg.load_definitions(units_file_path)
                logger.warning("done.")

            def names(self, names):
                self._names = names
            V1ContainerImage.names = V1ContainerImage.names.setter(names)
            k8s.config.load_incluster_config()
            NodeUtil.core_v1 = k8s.client.CoreV1Api()

        NodeUtil.enable = True if Variable.get(key="util_scheduling", default_var=None).lower() == "true" else False

        if not NodeUtil.enable:
            logger.warning("Util-scheduler is disabled!!")
            return True

        else:
            config = ti.executor_config
            if "ram_mem_mb" not in config:
                logger.warning("Execuexecutor_config not found!")
                logger.warning(ti.operator)
                logger.warning(ti)
                return False
            default_cpu = 70
            default_ram = 80
            NodeUtil.max_util_cpu = Variable.get(key="max_util_cpu", default_var=None)
            NodeUtil.max_util_ram = Variable.get(key="max_util_ram", default_var=None)
            if NodeUtil.max_util_cpu is None and NodeUtil.max_util_ram is None:
                Variable.set("max_util_cpu", default_cpu)
                Variable.set("max_util_ram", default_ram)
                NodeUtil.max_util_cpu = default_cpu
                NodeUtil.max_util_ram = default_ram
            else:
                NodeUtil.max_util_cpu = int(NodeUtil.max_util_cpu)
                NodeUtil.max_util_ram = int(NodeUtil.max_util_ram)

            now = datetime.now()
            if NodeUtil.last_update is None or (now - NodeUtil.last_update).seconds >= 3:
                util_result = NodeUtil.compute_allocated_resources(logger=logger)
                if not util_result:
                    logger.warning("############################################# COULD NOT FETCH UTILIZATION -> SKIPPING!")
                    return True

            NodeUtil.cpu_percent, return_code_cpu = NodeUtil.get_node_info(query=NodeUtil.cpu_util_per_query, logger=logger)
            if not return_code_cpu:
                logger.warning("############################################# Could not fetch cpu utilization from prometheus!!")

            Variable.set("CPU-Percent", "{}".format(NodeUtil.cpu_percent))
            if NodeUtil.cpu_percent is None or NodeUtil.cpu_percent > NodeUtil.max_util_cpu:
                logger.warning("############################################# High CPU utilization -> waiting!")
                logger.warning("############################################# cpu_percent: {}".format(NodeUtil.cpu_percent))
                return False

            NodeUtil.mem_percent, return_code_ram = NodeUtil.get_node_info(query=NodeUtil.mem_util_per_query, logger=logger)
            if not return_code_ram:
                logger.warning("############################################# Could not fetch ram utilization from prometheus!!")
            Variable.set("RAM-Percent", "{}".format(NodeUtil.mem_percent))
            if NodeUtil.mem_percent is None or NodeUtil.mem_percent > NodeUtil.max_util_ram:
                logger.warning("############################################# High RAM utilization -> waiting!")
                logger.warning("############################################# mem_percent: {}".format(NodeUtil.mem_percent))
                return False

            if not return_code_cpu or not return_code_ram:
                logger.warning("############################################# Could not fetch util from prometheus! -> waiting!")
                return False

            ti_ram_mem_mb = 0 if config["ram_mem_mb"] == None else config["ram_mem_mb"]
            ti_cpu_millicores = 0 if config["cpu_millicores"] == None else config["cpu_millicores"]
            ti_gpu_mem_mb = 0 if config["gpu_mem_mb"] == None else config["gpu_mem_mb"]

            if ti_ram_mem_mb >= NodeUtil.memory_available_req:
                # if ti_ram_mem_mb >= NodeUtil.memory_available_limit or ti_ram_mem_mb >= NodeUtil.memory_available_req:
                logger.warning("Not enough RAM -> not scheduling")
                logger.warning("MEM LIMIT: {}/{}".format(ti_ram_mem_mb, NodeUtil.memory_available_req))
                logger.warning("MEM REQ:   {}/{}".format(ti_ram_mem_mb, NodeUtil.memory_available_req))
                return False

            if ti_cpu_millicores >= NodeUtil.cpu_available_req:
                # if ti_cpu_millicores >= NodeUtil.cpu_available_limit or ti_cpu_millicores >= NodeUtil.cpu_available_req:
                logger.warning("Not enough CPU cores -> not scheduling")
                logger.warning("CPU LIMIT: {}/{}".format(ti_cpu_millicores, NodeUtil.cpu_available_req))
                logger.warning("CPU REQ:   {}/{}".format(ti_cpu_millicores, NodeUtil.cpu_available_req))
                return False

            if ti_gpu_mem_mb > NodeUtil.gpu_memory_available:
                logger.warning("Not enough GPU memory -> not scheduling")
                logger.warning("GPU: {}/{}".format(ti_gpu_mem_mb, NodeUtil.gpu_memory_available))
                return False

            tmp_memory_available_req = int(NodeUtil.memory_available_req - ti_ram_mem_mb)
            tmp_cpu_available_req = int(NodeUtil.cpu_available_req - ti_cpu_millicores)
            tmp_gpu_memory_available = int(NodeUtil.gpu_memory_available - ti_gpu_mem_mb)

            if tmp_memory_available_req < 0 or tmp_cpu_available_req < 0 or tmp_gpu_memory_available < 0:
                logger.error("############################################################### Error!")
                logger.error("Detected negative resource availability!")
                logger.error("memory_available_req: {}".format(tmp_memory_available_req))
                logger.error("cpu_available_req: {}".format(tmp_cpu_available_req))
                logger.error("gpu_memory_available: {}".format(tmp_gpu_memory_available))
                return False

            NodeUtil.memory_available_req = tmp_memory_available_req
            NodeUtil.cpu_available_req = tmp_cpu_available_req
            NodeUtil.gpu_memory_available = tmp_gpu_memory_available
            NodeUtil.mem_req = NodeUtil.mem_req + ti_ram_mem_mb
            NodeUtil.mem_lmt = NodeUtil.mem_lmt + ti_ram_mem_mb

            Variable.set("RAM-Node", "{}".format(NodeUtil.mem_alloc))
            Variable.set("RAM-Available", "{}".format(NodeUtil.memory_available_req))
            Variable.set("RAM-Requested", "{}".format(NodeUtil.mem_req))
            Variable.set("RAM-Limit", "{}".format(NodeUtil.mem_lmt))
            Variable.set("CPU", "{}/{}".format(NodeUtil.cpu_lmt+ti_cpu_millicores, NodeUtil.cpu_alloc))
            Variable.set("CPU-Available", "{}".format(NodeUtil.cpu_available_limit))
            Variable.set("GPU", "{}/{}".format(NodeUtil.gpu_used+ti_gpu_mem_mb, NodeUtil.gpu_alloc))
            Variable.set("GPU-Available", "{}".format(NodeUtil.gpu_memory_available))
            Variable.set("UPDATED", datetime.utcnow())

            return True
