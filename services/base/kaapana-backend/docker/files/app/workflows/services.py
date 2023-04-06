import requests
import logging
import json
from typing import Any, Tuple
from fastapi import HTTPException
from app.experiments import utils


class WorkflowService:
    def __init__(self, airflow_api: str):
        self.airflow_api = airflow_api
        self.log = logging.getLogger(__name__)
        self.log.info(
            "Initalized WorkflowService (using %s as airflow endpoint", airflow_api
        )

    def __get_airflow_api_json(
        self, url: str, params: dict = None, text_response: bool = False
    ) -> Tuple[Any, HTTPException]:
        req_url = self.airflow_api + url
        r = requests.get(req_url, params=params)
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.log.error(e)
            return (
                None,
                HTTPException(
                    status_code=r.status_code, detail="{0} {1}".format(e, r.text)
                ),
            )

        if text_response:
            return ({"message": r.text, "status_code": r.status_code}, None)

        return (r.json(), None)

    def get_dags(self) -> Tuple[Any, HTTPException]:
        resp, err = self.__get_airflow_api_json("/getdags")
        return (list(resp.keys()), err)

    def trigger_workflow(
        self, db_client_kaapana: Any, conf_data: dict, dry_run: str = True
    ) -> Tuple[Any, HTTPException]:
        if conf_data["conf"]["dag"] not in json.loads(db_client_kaapana.allowed_dags):
            return (
                None,
                HTTPException(
                    status_code=403,
                    detail=f"Dag {conf_data['conf']['dag']} is not allowed to be triggered from remote!",
                ),
            )
        return None
        # queried_data = crud.get_datasets(
        #     {'query': conf_data['conf']['query']}
        # )

        if not all(
            [
                bool(set(d) & set(json.loads(db_client_kaapana.allowed_datasets)))
                for d in queried_data
            ]
        ):
            return (
                None,
                HTTPException(
                    status_code=403,
                    detail=f"Your query outputed data with the tags: "
                    f"{''.join(sorted(list(set([d for datasets in queried_data for d in datasets]))))}, "
                    f"but only the following tags are allowed to be used from remote: {','.join(json.loads(db_client_kaapana.allowed_datasets))} !",
                ),
            )
        if dry_run is True:
            return (
                f"The configuration for the allowed dags and datasets is okay!",
                None,
            )
        r = requests.post(self.airflow_api + "/trigger/meta-trigger", json=conf_data)

        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.log.error(e)
            return (
                None,
                HTTPException(
                    status_code=r.status_code, detail="{0} {1}".format(e, r.text)
                ),
            )
        return (r.json(), None)

    def get_running_dags(self) -> Tuple[Any, HTTPException]:
        r_dags, err = self.__get_airflow_api_json("/getdags")
        if err:
            return (None, err)

        dags = list(r_dags.keys())
        running_dags = []
        for dag_id in dags:
            r, err = self.__get_airflow_api_json(
                "/dags/{0}/dagRuns/state/running/count".format(dag_id)
            )
            if err:
                return (None, err)
            num_runs = r["number_of_dagruns"]
            if num_runs > 0:
                running_dags.append(dag_id)

        return (running_dags, None)

    def get_dag_history(self, dag_id: str) -> Tuple[Any, HTTPException]:
        ###### returns [dag_id] for currently running DAGs ######
        r, err = self.__get_airflow_api_json("/dagids/{0}".format(dag_id))
        if err:
            return (None, err)
        return (r, None)
