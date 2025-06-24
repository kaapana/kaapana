import requests
from ..config import settings

from fastapi import (
    APIRouter,
    Request,
    HTTPException,
)
from typing import List
from pydantic import BaseModel
import time
import json
from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb

class Dataseries(BaseModel):
    imageSeries: list
    additionalImageSeries: list


router = APIRouter()


def execute_job_airflow(conf_data, db_job):
    print(f"Triggering DAG {db_job.dag_id} with conf_data: {conf_data}")
    with requests.Session() as s:
        resp = s.post(
            f"http://airflow-webserver-service.{settings.services_namespace}.svc:8080/flow/kaapana/api/trigger/{db_job.dag_id}",
            json={
                "conf": {
                    **conf_data,
                }
            },
        )
    return resp


@router.get("/")
async def root(request: Request):
    return {
        "message": "Welcome to the m2olie api",
        "root_path": request.scope.get("root_path"),
    }


@router.get("/getImageSeries")
def get_images_series(studyUid: str):
    """
    Fetches image series for a given study UID from the DICOMweb service.
    Returns a list of dictionaries containing seriesUID and seriesDescription.
    """
    print(f"Fetching image series for study UID: {studyUid}")
    dicomweb_helper = HelperDcmWeb()
    
    url = f"{dicomweb_helper.dcmweb_rs_endpoint}/studies/{studyUid}/series"

    response = dicomweb_helper.session.get(url)
    print(f"Response status code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        series_list = []
        for item in data:
            seriesUID = item["0020000E"]["Value"][0]
            series_description = (
                item["0008103E"]["Value"][0]
                if "0008103E" in item and "Value" in item["0008103E"]
                else "NA"
            )
            series_dict = {
                "seriesUID": seriesUID,
                "seriesDescription": series_description,
            }
            series_list.append(series_dict)

        return series_list

    elif response.status_code == 204:
        return None  # The search completed successfully, but there were zero results.
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Error accessing url {response.url}, errorcode {response.status_code}",
        )


@router.post("/startWorkflow")
async def start_workflow(
    dagId: str,
    processInstanceLabel: str,
    taskLabel: str,
    prometheus_uri: str,
    dataseries: Dataseries,
    request: Request,
):
    conf_data = dict()
    project = request.headers.get("Project")
    conf_data["data_form"] = {
        "identifiers": dataseries.imageSeries,
        "cohort_query": {"index": ["meta-index"]},
        "workflow_form": {
            "single_execution": False,
            "task_label": taskLabel,
            "process_instance_label": processInstanceLabel,
            "additional_identifiers": dataseries.additionalImageSeries,
            "prometheus_uri": prometheus_uri,
        },
    }
    conf_data["project_form"] = json.loads(project)
    db_job = type("db_job", (object,), {"dag_id": dagId})
    response = execute_job_airflow(conf_data=conf_data, db_job=db_job)
    # trigger_info = response.json()
    # print(trigger_info)
    # run_id = trigger_info["message"][1]["run_id"]
    # workflow_running = True
    # while workflow_running:
    #     # check_workflow_is_running(run_id)  # implement this function to check if the workflow is still running
    #     resp_dagrun = get_dagrun_details_airflow(dagId, run_id)
    #     if resp_dagrun.status_code == 200:
    #         print(resp_dagrun.content)
    #         content = resp_dagrun.json()
    #         state = content["state"]
    #         if state != "queued" and state != "running":
    #             workflow_running = False
    #     # response = get_dagrun_tasks_airflow() not used, since no task details are needed
    #     time.sleep(15)
    return response.content
