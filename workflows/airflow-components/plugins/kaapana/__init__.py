from airflow.models import Variable
from kaapana.kubetools.utilization_service import UtilService
from kaapana.kubetools.kaapana_pool_manager import KaapanaPoolManager
from threading import Event
from os import getenv
import logging

airflow_mode = getenv("AIRFLOW_MODE", None)
logging.error(f"{airflow_mode=}")
if airflow_mode == "init":
    KaapanaPoolManager.check_pools(force=True)

elif airflow_mode == "webserver":
    enable_pool_manager = True if Variable.get("enable_pool_manager").lower() == "true" else False
    pool_manager_delay = int(Variable.get("pool_manager_delay"))

    if KaapanaPoolManager.self_object != None:
        logging.error(f"Is alive {KaapanaPoolManager.self_object.is_alive()}")

    if (KaapanaPoolManager.self_object == None or not KaapanaPoolManager.self_object.is_alive()) and enable_pool_manager:
        logging.error("KaapanaPoolManager activated -> starting service ...")
        KaapanaPoolManager.stopFlag = Event()
        KaapanaPoolManager.query_delay = pool_manager_delay
        KaapanaPoolManager.self_object = KaapanaPoolManager(event=KaapanaPoolManager.stopFlag)
        KaapanaPoolManager.self_object.start()

    elif KaapanaPoolManager.self_object != None and KaapanaPoolManager.self_object.is_alive() and not enable_pool_manager:
        logging.error("KaapanaPoolManager deactivated -> shutting down ...")
        KaapanaPoolManager.stopFlag.set()
        KaapanaPoolManager.stopFlag = Event()

    elif KaapanaPoolManager.self_object != None and KaapanaPoolManager.self_object.is_alive() and KaapanaPoolManager.query_delay != pool_manager_delay:
        logging.error("KaapanaPoolManager alive and different delay ...")
        KaapanaPoolManager.stopFlag.set()
        KaapanaPoolManager.query_delay = pool_manager_delay
        KaapanaPoolManager.stopFlag = Event()
        KaapanaPoolManager.self_object = KaapanaPoolManager(event=KaapanaPoolManager.stopFlag)
        KaapanaPoolManager.self_object.start()

    elif KaapanaPoolManager.self_object != None and KaapanaPoolManager.self_object.is_alive():
        logging.error("KaapanaPoolManager is running")
    else:
        logging.error("KaapanaPoolManager nothing to do ...")


elif airflow_mode == "scheduler":
    enable_job_scheduler = True if Variable.get("enable_job_scheduler").lower() == "true" else False
    job_scheduler_delay = int(Variable.get("job_scheduler_delay"))

    if UtilService.self_object == None:
    # if (UtilService.self_object == None or not UtilService.self_object.is_alive()) and enable_job_scheduler:
        logging.error("KaapanaUtilServive activated -> starting service ...")
        UtilService.stopFlag = Event()
        UtilService.query_delay = job_scheduler_delay
        UtilService.self_object = UtilService(event=UtilService.stopFlag)
        # UtilService.self_object.start()

    # elif UtilService.self_object != None and UtilService.self_object.is_alive() and not enable_job_scheduler:
    #     logging.error("KaapanaUtilServive deactivated -> shutting down ...")
    #     UtilService.stopFlag.set()
    #     UtilService.stopFlag = Event()

    # elif UtilService.self_object != None and UtilService.self_object.is_alive() and UtilService.query_delay != job_scheduler_delay:
    #     logging.error("airflow_mode == scheduler - 4")
    #     UtilService.stopFlag.set()
    #     UtilService.query_delay = job_scheduler_delay
    #     UtilService.stopFlag = Event()
    #     thread = UtilService(event=UtilService.stopFlag)
    #     thread.start()
    # else:
    #     logging.error("KaapanaUtilServive already running")
        
    UtilService.get_utilization()