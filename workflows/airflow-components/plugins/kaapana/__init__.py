from airflow.models import Variable
from kaapana.kubetools.utilization_service import UtilService
from kaapana.kubetools.kaapana_pool_manager import KaapanaPoolManager
from threading import Event
from os import getenv
import logging

airflow_mode = getenv("AIRFLOW_MODE", None)
logging.error(f"{airflow_mode=}")
if airflow_mode == "init":
    pass

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
    if UtilService.last_update == None: 
        UtilService.init_util_service()
