import requests
from ..config import settings
from app.experiments.utils import execute_job_airflow, get_dagrun_details_airflow
from fastapi import (
    APIRouter,
    Depends,
    Request,
    HTTPException,
    UploadFile,
    Response,
    File,
    Header,
)
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import time


class Dataseries(BaseModel):
    imageSeries: list


router = APIRouter()


@router.get("/")
async def root(request: Request):
    return {
        "message": "Welcome to the m2olie api",
        "root_path": request.scope.get("root_path"),
    }


@router.get("/getImageSeries")
def get_images_series(studyUid: str):
    url = settings.dcm4chee_url + "studies/" + studyUid + "/series"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        series_list = []
        for item in data:
            seriesUID = item["0020000E"]["Value"][0]
            series_description = item["0008103E"]["Value"][0]
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
    dataseries: Dataseries,
):

    conf_data = dict()
    conf_data["data_form"] = {
        "cohort_identifiers": dataseries.imageSeries,
        "cohort_query": {"index": ["meta-index"]},
        "workflow_form": {
            "single_execution": False,
            "task_label": taskLabel,
            "process_instance_label": processInstanceLabel,
        },
    }
    db_job = type("db_job", (object,), {"dag_id": dagId})
    response = execute_job_airflow(conf_data=conf_data, db_job=db_job)
    trigger_info = response.json()
    print(trigger_info)
    run_id = trigger_info["message"][1]["run_id"]
    workflow_running = True
    while workflow_running:
        # check_workflow_is_running(run_id)  # implement this function to check if the workflow is still running
        resp_dagrun = get_dagrun_details_airflow(dagId, run_id)
        if resp_dagrun.status_code == 200:
            print(resp_dagrun.content)
            content = resp_dagrun.json()
            state = content["state"]
            if state != "queued" and state != "running":
                workflow_running = False
        # response = get_dagrun_tasks_airflow() not used, since no task details are needed
        time.sleep(15)
    return response.content
