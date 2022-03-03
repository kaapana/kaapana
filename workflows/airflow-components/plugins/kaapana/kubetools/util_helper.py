import kubernetes as k8s
from pint import UnitRegistry
from collections import defaultdict
from datetime import datetime
import os, json
from kaapana.kubetools.prometheus_query import get_node_memory, get_node_mem_percent, get_node_cpu, \
    get_node_cpu_util_percent, get_node_gpu_infos
from airflow.models import Variable
from airflow.models import Pool as pool_api
from kubernetes.client.models.v1_container_image import V1ContainerImage
from pprint import pprint
from airflow.utils.state import State
from typing import Any, Optional


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
    gpu_dev_count = None

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

    @staticmethod
    def python_value_from_airflow_json_file(key: str, default_var: Any = None):
        try:
            # Get a file object with write permission.
            file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'kaapana_utils.json')
            with open(file_path, 'r') as file_object:
                try:
                    json_object = json.load(file_object)
                except ValueError:
                    print("file is not a json yet.")
                    return default_var
            if key in json_object:
                return json_object[key]
        except FileNotFoundError or ValueError:
            print(file_path + " not found. ")
        return default_var

    @staticmethod
    def python_value_to_airflow_json_file(key: str, value: Any):
        try:
            file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'kaapana_utils.json')
            with open(file_path, 'r') as file_object:
                try:
                    json_object = json.load(file_object)
                except ValueError:
                    print("file does not exist yet.")
                    json_object = {}
        except FileNotFoundError:
            print(file_path + " not set. ")
            json_object = {}
        if key in json_object and json_object[key] == value:
            return
        json_object[key] = value
        with open(file_path, 'w') as file_object:
            json.dump(json_object, file_object, ensure_ascii=False, indent=4, default=str)

    @staticmethod
    def get_variable(key: str, default_var: Any = None):
        # var = Variable.get(key=key,default_var=default_var)
        return NodeUtil.python_value_from_airflow_json_file(key=key, default_var=default_var)

    @staticmethod
    def set_variable(key: str, value: Any, description: Optional[str] = None):
        # Variable.set(key=key,value=value, description=description)
        NodeUtil.python_value_to_airflow_json_file(key=key, value=value)

    @staticmethod
    def get_pool_by_name(session, name):
        try:
            # important: provide session here, otherwise a new session will be created here,
            # destroying the current session of the caller function.
            pool = pool_api.get_pool(name, session)
            return pool
        except Exception as e:
            return None

    @staticmethod
    def check_gpu_pools(session, logger=None):
        if NodeUtil.gpu_dev_count == None:
            NodeUtil.check_ti_scheduling(task_instance=None, session=session, logger=None)
        gpu_count_pool = NodeUtil.get_pool_by_name(session=session, name="GPU_COUNT")
        if gpu_count_pool is None or gpu_count_pool.slots != NodeUtil.gpu_dev_count:
            if NodeUtil.gpu_dev_count > 0:
                NodeUtil.set_variable("GPU_SUPPORT", "True")
                pool_api.create_or_update_pool(
                    name="GPU_COUNT",
                    slots=NodeUtil.gpu_dev_count,
                    description="Count of GPUs of the node",
                    session=session
                )
            else:
                NodeUtil.set_variable("GPU_SUPPORT", "False")

        gpu_infos = get_node_gpu_infos()
        for gpu in gpu_infos:
            gpu_pool_id = f"GPU_{gpu['id']}_CAPACITY"
            gpu_pool = NodeUtil.get_pool_by_name(session=session, name=gpu_pool_id)
            if gpu_pool == None or gpu["mem_capacity"] != gpu_pool.slots:
                pool_api.create_or_update_pool(
                    name=gpu_pool_id,
                    slots=gpu["mem_capacity"],
                    description=f"Mem capacity of {gpu['name']}",
                    session=session
                )

    @staticmethod
    def compute_allocated_resources(session, logger=None):
        Q_ = NodeUtil.ureg.Quantity
        data = {}
        NodeUtil.last_update = datetime.now()

        try:
            for node in NodeUtil.core_v1.list_node().items:
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

                stats["cpu_alloc"] = Q_(allocatable["cpu"])
                stats["mem_alloc"] = Q_(allocatable["memory"])
                stats["gpu_dev_count"] = Q_(capacity["nvidia.com/gpu"] if "nvidia.com/gpu" in capacity else 0)
                stats["gpu_dev_free"] = Q_(allocatable["nvidia.com/gpu"] if "nvidia.com/gpu" in allocatable else 0)

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
            NodeUtil.gpu_dev_count = int(node_info["gpu_dev_count"])
            NodeUtil.gpu_dev_free = int(node_info["gpu_dev_free"])
            NodeUtil.memory_pressure = node_info["memory_pressure"]
            NodeUtil.disk_pressure = node_info["disk_pressure"]
            NodeUtil.pid_pressure = node_info["pid_pressure"]

            NodeUtil.check_gpu_pools(session=session, logger=logger)
            NodeUtil.cpu_available_req = NodeUtil.cpu_alloc - NodeUtil.cpu_req
            NodeUtil.cpu_available_limit = NodeUtil.cpu_alloc - NodeUtil.cpu_lmt
            NodeUtil.memory_available_req = NodeUtil.mem_alloc - NodeUtil.mem_req
            NodeUtil.memory_available_limit = NodeUtil.mem_alloc - NodeUtil.mem_lmt
            # NodeUtil.gpu_memory_available = None if (NodeUtil.gpu_mem_alloc is None or NodeUtil.gpu_mem_used is None) else (NodeUtil.gpu_mem_alloc - NodeUtil.gpu_mem_used)

            NodeUtil.set_variable("CPU_NODE", "{}/{}".format(NodeUtil.cpu_lmt, NodeUtil.cpu_alloc))
            NodeUtil.set_variable("CPU_FREE", "{}".format(NodeUtil.cpu_available_req))
            NodeUtil.set_variable("RAM_NODE", "{}/{}".format(NodeUtil.mem_req, NodeUtil.mem_alloc))
            NodeUtil.set_variable("RAM_FREE", "{}".format(NodeUtil.memory_available_req))
            # NodeUtil.set_variable("GPU_DEV_COUNT", "{}/{}".format(NodeUtil.gpu_dev_count))
            # NodeUtil.set_variable("GPU_DEV_FREE", "{}".format(NodeUtil.gpu_dev_free))
            # NodeUtil.set_variable("GPU_MEM", "{}/{}".format(NodeUtil.gpu_mem_used, NodeUtil.gpu_mem_alloc))
            # NodeUtil.set_variable("GPU_MEM_FREE", "{}".format(NodeUtil.gpu_memory_available))
            NodeUtil.set_variable("UPDATED", datetime.utcnow())
            # NodeUtil.set_variable("cpu_alloc", "{}".format(NodeUtil.cpu_alloc))
            # NodeUtil.set_variable("cpu_req", "{}".format(NodeUtil.cpu_req))
            # NodeUtil.set_variable("cpu_lmt", "{}".format(NodeUtil.cpu_lmt))
            # NodeUtil.set_variable("cpu_req_per", "{}".format(NodeUtil.cpu_req_per))
            # NodeUtil.set_variable("cpu_lmt_per", "{}".format(NodeUtil.cpu_lmt_per))
            # NodeUtil.set_variable("cpu_available_req", "{}".format(NodeUtil.cpu_available_req))
            # NodeUtil.set_variable("cpu_available_limit", "{}".format(NodeUtil.cpu_available_limit))
            # NodeUtil.set_variable("mem_alloc", "{}".format(NodeUtil.mem_alloc))
            # NodeUtil.set_variable("mem_req", "{}".format(NodeUtil.mem_req))
            # NodeUtil.set_variable("mem_lmt", "{}".format(NodeUtil.mem_lmt))
            # NodeUtil.set_variable("mem_req_per", "{}".format(NodeUtil.mem_req_per))
            # NodeUtil.set_variable("mem_lmt_per", "{}".format(NodeUtil.mem_lmt_per))
            # NodeUtil.set_variable("memory_available_req", "{}".format(NodeUtil.memory_available_req))
            # NodeUtil.set_variable("memory_available_limit", "{}".format(NodeUtil.memory_available_limit))
            # NodeUtil.set_variable("gpu_count", "{}".format(NodeUtil.gpu_count))
            # NodeUtil.set_variable("gpu_alloc", "{}".format(NodeUtil.gpu_alloc))
            # NodeUtil.set_variable("gpu_used", "{}".format(NodeUtil.gpu_used))
            # NodeUtil.set_variable("gpu_memory_available", "{}".format(NodeUtil.gpu_memory_available))
            return True

        except Exception as e:
            print("+++++++++++++++++++++++++++++++++++++++++ COULD NOT FETCH NODES!")
            print(e)
            return False

    @staticmethod
    def check_ti_scheduling(task_instance, session, logger):
        if NodeUtil.ureg is None:
            if logger != None:
                logger.warning("Inititalize Util-Helper!")

            NodeUtil.enable = NodeUtil.get_variable(key="util_scheduling", default_var=None)
            if NodeUtil.enable == None:
                print("Setting util_scheduling.")
                NodeUtil.set_variable("util_scheduling", True)
                NodeUtil.enable = 'True'

            if logger != None:
                logger.warning("-> init UnitRegistry...")
            NodeUtil.ureg = UnitRegistry()
            units_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'kubernetes_units.txt')
            if not os.path.isfile(units_file_path):
                if logger != None:
                    logger.warning("Could not find kubernetes_units.txt @  {} !".format(units_file_path))
                    logger.warning("abort.")
                exit(1)
            else:
                NodeUtil.ureg.load_definitions(units_file_path)

            def names(self, names):
                self._names = names

            V1ContainerImage.names = V1ContainerImage.names.setter(names)
            k8s.config.load_incluster_config()
            NodeUtil.core_v1 = k8s.client.CoreV1Api()

        NodeUtil.enable = NodeUtil.get_variable(key="util_scheduling", default_var=True)
        if not NodeUtil.enable or task_instance == None:
            NodeUtil.compute_allocated_resources(session=session, logger=logger)
            if logger != None:
                logger.warning("Util-scheduler is disabled!!")
            return True

        else:
            config = task_instance.executor_config
            if "ram_mem_mb" not in config:
                if logger != None:
                    logger.warning("Execuexecutor_config not found!")
                    logger.warning(task_instance.operator)
                    logger.warning(task_instance)
                return False
            default_cpu = 70
            default_ram = 80
            NodeUtil.max_util_cpu = NodeUtil.get_variable(key="max_util_cpu", default_var=None)
            NodeUtil.max_util_ram = NodeUtil.get_variable(key="max_util_ram", default_var=None)
            if NodeUtil.max_util_cpu is None and NodeUtil.max_util_ram is None:
                NodeUtil.set_variable("max_util_cpu", default_cpu)
                NodeUtil.set_variable("max_util_ram", default_ram)
                NodeUtil.max_util_cpu = default_cpu
                NodeUtil.max_util_ram = default_ram
            else:
                NodeUtil.max_util_cpu = int(NodeUtil.max_util_cpu)
                NodeUtil.max_util_ram = int(NodeUtil.max_util_ram)

            now = datetime.now()
            if NodeUtil.last_update is None or (now - NodeUtil.last_update).seconds >= 3:
                util_result = NodeUtil.compute_allocated_resources(session=session, logger=logger)
                if not util_result:
                    logger.warning(
                        "############################################# COULD NOT FETCH UTILIZATION -> SKIPPING!")
                    return True
            NodeUtil.cpu_percent = get_node_cpu_util_percent(logger=logger)
            if NodeUtil.cpu_percent is None or NodeUtil.cpu_percent > NodeUtil.max_util_cpu:
                if logger != None:
                    logger.warning("############################################# High CPU utilization -> waiting!")
                    logger.warning(
                        "############################################# cpu_percent: {}".format(NodeUtil.cpu_percent))
                return False
            NodeUtil.set_variable("CPU_PERCENT", "{}".format(NodeUtil.cpu_percent))

            NodeUtil.mem_percent = get_node_mem_percent()

            if NodeUtil.mem_percent is None or NodeUtil.mem_percent > NodeUtil.max_util_ram:
                if logger != None:
                    logger.warning("############################################# High RAM utilization -> waiting!")
                    logger.warning(
                        "############################################# mem_percent: {}".format(NodeUtil.mem_percent))
                return False
            NodeUtil.set_variable("RAM_PERCENT", "{}".format(NodeUtil.mem_percent))

            if NodeUtil.memory_pressure:
                if logger != None:
                    logger.warning(
                        "##########################################################################################")
                    logger.warning(
                        "#################################### Instable system! ####################################")
                    logger.warning(
                        "##################################### memory_pressure ####################################")
                    logger.warning(
                        "##########################################################################################")
                return False

            if NodeUtil.disk_pressure:
                if logger != None:
                    logger.warning(
                        "##########################################################################################")
                    logger.warning(
                        "#################################### Instable system! ####################################")
                    logger.warning(
                        "##################################### disk_pressure ####################################")
                    logger.warning(
                        "##########################################################################################")
                return False

            if NodeUtil.pid_pressure:
                if logger != None:
                    logger.warning(
                        "##########################################################################################")
                    logger.warning(
                        "#################################### Instable system! ####################################")
                    logger.warning(
                        "##################################### pid_pressure ####################################")
                    logger.warning(
                        "##########################################################################################")
                return False

            ti_ram_mem_mb = 0 if config["ram_mem_mb"] == None else config["ram_mem_mb"]
            ti_cpu_millicores = 0 if config["cpu_millicores"] == None else config["cpu_millicores"]
            # ti_gpu_mem_mb = 0 if config["gpu_mem_mb"] == None else config["gpu_mem_mb"]
            if ti_ram_mem_mb >= NodeUtil.memory_available_req:
                if logger != None:
                    # if ti_ram_mem_mb >= NodeUtil.memory_available_limit or ti_ram_mem_mb >= NodeUtil.memory_available_req:
                    logger.warning("Not enough RAM -> not scheduling")
                    logger.warning("MEM LIMIT: {}/{}".format(ti_ram_mem_mb, NodeUtil.memory_available_req))
                    logger.warning("MEM REQ:   {}/{}".format(ti_ram_mem_mb, NodeUtil.memory_available_req))
                return False

            if ti_cpu_millicores >= NodeUtil.cpu_available_req:
                if logger != None:
                    # if ti_cpu_millicores >= NodeUtil.cpu_available_limit or ti_cpu_millicores >= NodeUtil.cpu_available_req:
                    logger.warning("Not enough CPU cores -> not scheduling")
                    logger.warning("CPU LIMIT: {}/{}".format(ti_cpu_millicores, NodeUtil.cpu_available_req))
                    logger.warning("CPU REQ:   {}/{}".format(ti_cpu_millicores, NodeUtil.cpu_available_req))
                return False
            # if ti_gpu_mem_mb > 0 and NodeUtil.gpu_dev_free <= 1:
            #     logger.warning("All GPUs are in currently in use -> not scheduling")
            #     return False

            # if NodeUtil.gpu_memory_available is not None and ti_gpu_mem_mb > NodeUtil.gpu_memory_available:
            #     logger.warning("Not enough GPU memory -> not scheduling")
            #     logger.warning("GPU: {}/{}".format(ti_gpu_mem_mb, NodeUtil.gpu_memory_available))
            #     return False

            tmp_memory_available_req = int(NodeUtil.memory_available_req - ti_ram_mem_mb)
            tmp_cpu_available_req = int(NodeUtil.cpu_available_req - ti_cpu_millicores)
            # tmp_gpu_memory_available = int(NodeUtil.gpu_memory_available - ti_gpu_mem_mb)

            if tmp_memory_available_req < 0 or tmp_cpu_available_req < 0:
                if logger != None:
                    logger.error("############################################################### Error!")
                    logger.error("Detected negative resource availability!")
                    logger.error("memory_available_req: {}".format(tmp_memory_available_req))
                    logger.error("cpu_available_req: {}".format(tmp_cpu_available_req))
                return False

            NodeUtil.memory_available_req = tmp_memory_available_req
            NodeUtil.cpu_available_req = tmp_cpu_available_req
            # NodeUtil.gpu_memory_available = tmp_gpu_memory_available
            # NodeUtil.gpu_dev_free = max(0, NodeUtil.gpu_dev_free)
            NodeUtil.mem_req = NodeUtil.mem_req + ti_ram_mem_mb
            NodeUtil.mem_lmt = NodeUtil.mem_lmt + ti_ram_mem_mb

            NodeUtil.set_variable("CPU_NODE", "{}/{}".format(NodeUtil.cpu_lmt, NodeUtil.cpu_alloc))
            NodeUtil.set_variable("CPU_FREE", "{}".format(NodeUtil.cpu_available_req))
            NodeUtil.set_variable("RAM_NODE", "{}/{}".format(NodeUtil.mem_req, NodeUtil.mem_alloc))
            NodeUtil.set_variable("RAM_FREE", "{}".format(NodeUtil.memory_available_req))
            # NodeUtil.set_variable("GPU_DEV_COUNT", "{}/{}".format(NodeUtil.gpu_dev_count))
            # NodeUtil.set_variable("GPU_DEV_FREE", "{}".format(NodeUtil.gpu_dev_free))
            # NodeUtil.set_variable("GPU_MEM", "{}/{}".format(NodeUtil.gpu_mem_used, NodeUtil.gpu_mem_alloc))
            # NodeUtil.set_variable("GPU_MEM_FREE", "{}".format(NodeUtil.gpu_memory_available))
            NodeUtil.set_variable("UPDATED", datetime.utcnow())
            return True


def get_gpu_pool(task_instance, session, logger):
    logger.error(f"################ task_id:    {task_instance.task_id}")
    logger.error(f"################ GPU-MEM:    {task_instance.pool_slots}")
    queued_gpu_slots = []
    if NodeUtil.gpu_dev_count == None:
        NodeUtil.check_ti_scheduling(task_instance=None, session=session, logger=logger)
    for i in range(0, NodeUtil.gpu_dev_count):
        gpu_pool_id = f"GPU_{i}_CAPACITY"
        gpu_pool = NodeUtil.get_pool_by_name(session=session, name=gpu_pool_id)
        if gpu_pool == None:
            NodeUtil.check_gpu_pools(session, logger)
            gpu_pool = NodeUtil.get_pool_by_name(session=session, name=gpu_pool_id)

        if gpu_pool != None and gpu_pool.slots > task_instance.pool_slots:
            capacity = gpu_pool.slots
            used = gpu_pool.occupied_slots()
            # running_slots = gpu_pool.running_slots()
            queued_slots = gpu_pool.queued_slots()
            queued_gpu_slots.append({
                "id": i,
                "pool_id": gpu_pool_id,
                "pool_slots": gpu_pool.slots,
                "queued_slots": queued_slots
            })
            free = capacity - used
            logger.error(f"################ GPU:      {i}")
            logger.error(f"################ capacity: {capacity}")
            logger.error(f"################ used:     {used}")
            logger.error(f"################ free:     {free}")
            if task_instance.pool_slots >= free:
                logger.error(f"################ Not enough memory!")
            else:
                logger.error(f"################ memory ok!")
                task_instance.pool = gpu_pool_id
                break

    if task_instance.pool == "GPU_COUNT":
        if len(queued_gpu_slots) > 0:
            pool_id = None
            min_queue = None
            for gpu in queued_gpu_slots:
                if pool_id == None or min_queue == None or gpu["queued_slots"] < min_queue:
                    pool_id = gpu["pool_id"]
                    min_queue = gpu["queued_slots"]
            task_instance.pool = pool_id
        else:
            task_instance.pool = "GPU_COUNT"
            task_instance.pool_slots = 1
            task_instance.state = State.FAILED
            task_instance.log.error(f"################################################################")
            task_instance.log.error(f"#")
            task_instance.log.error(f"################   GPU needed and not found !   ################")
            task_instance.log.error(f"#")
            task_instance.log.error(f"################################################################")

    return task_instance