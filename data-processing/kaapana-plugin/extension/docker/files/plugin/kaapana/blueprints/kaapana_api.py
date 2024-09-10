import json
from http import HTTPStatus

from airflow import settings
from airflow.api.common.trigger_dag import trigger_dag as trigger
from airflow.api.common.experimental.mark_tasks import (
    set_dag_run_state_to_failed as set_dag_run_failed,
)
from airflow.exceptions import AirflowException
from airflow.models import DagRun, DagModel, DagBag, DAG
from airflow.models.taskinstance import TaskInstance
from airflow.utils.state import State, TaskInstanceState, DagRunState
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.www.app import csrf
from airflow.utils import timezone

from flask import Blueprint, request, jsonify, Response
from flask import current_app as app

from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound

from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
from kaapana.blueprints.kaapana_utils import (
    generate_run_id,
    generate_minio_credentials,
    parse_ui_dict,
)
from kaapana.operators.HelperOpensearch import HelperOpensearch

_log = LoggingMixin().log
parallel_processes = 1
"""
Represents a blueprint kaapanaApi
"""
kaapanaApi = Blueprint("kaapana", __name__, url_prefix="/kaapana")


@csrf.exempt
@kaapanaApi.route("/api/trigger/<string:dag_id>", methods=["POST"])
def trigger_dag(dag_id):
    # headers = dict(request.headers)
    data = request.get_json(force=True)
    # username = headers["X-Forwarded-Preferred-Username"] if "X-Forwarded-Preferred-Username" in headers else "unknown"
    if "conf" in data:
        tmp_conf = data["conf"]
    else:
        tmp_conf = data

    # For authentication
    if "x_auth_token" in data:
        tmp_conf["x_auth_token"] = data["x_auth_token"]
    else:
        tmp_conf["x_auth_token"] = request.headers.get("X-Auth-Token")

    ################################################################################################
    #### Deprecated! Will be removed with the next version 0.3.0

    if (
        "workflow_form" in tmp_conf
    ):  # in the future only workflow_form should be included in the tmp_conf
        tmp_conf["form_data"] = tmp_conf["workflow_form"]
    elif "form_data" in tmp_conf:
        tmp_conf["workflow_form"] = tmp_conf["form_data"]

    ################################################################################################

    if "run_id" in data and data["run_id"] is not None:
        run_id = data["run_id"]
    else:
        run_id = generate_run_id(dag_id)

    print(json.dumps(tmp_conf, indent=2))

    execution_date = None
    try:
        dr = trigger(
            dag_id, run_id, tmp_conf, execution_date, replace_microseconds=False
        )
    except AirflowException as err:
        _log.error(err)
        response = jsonify(error="{}".format(err))
        response.status_code = err.status_code
        return response

    message = ["{} created!".format(dr.dag_id)]
    dag_dagrun_dict = {}
    dag_dagrun_dict["dag_id"] = dr.dag_id
    dag_dagrun_dict["run_id"] = dr.run_id
    message.append(dag_dagrun_dict)
    response = jsonify(message=message)
    return response


@csrf.exempt
@kaapanaApi.route("/api/get_dagrun_tasks/<dag_id>/<run_id>", methods=["POST"])
def get_dagrun_tasks(dag_id, run_id):
    """
    This Airflow API does the following:
    - query from airflow a dag_run by dag_id and run_id
    - get all tasks including their states of queried dag_run
    - return tasks
    """
    dag_objects = DagBag().dags  # returns all DAGs available on platform
    desired_dag = dag_objects[
        dag_id
    ]  # filter desired_dag from all available dags via dag_id
    session = settings.Session()
    message = []

    task_ids = [
        task.task_id for task in desired_dag.tasks
    ]  # get task_ids of desired_dag
    tis = session.query(
        TaskInstance
    ).filter(  # query TaskInstances which are part of desired_dag wit run_id=run_id and task_ids
        TaskInstance.dag_id == desired_dag.dag_id,
        TaskInstance.run_id == run_id,
        TaskInstance.task_id.in_(task_ids),
    )
    tis = [ti for ti in tis]

    # compose 2 response dict in style: {"task_instance": "state"/"execution_date"}
    state_dict = {}
    exdate_dict = {}
    for ti in tis:
        state_dict[ti.task_id] = ti.state
        exdate_dict[ti.task_id] = str(ti.execution_date)

    # message.append(f"Result of task querying: {tis}")
    message.append(f"{state_dict}")
    message.append(f"{exdate_dict}")
    response = jsonify(message=message)
    return response


@csrf.exempt
@kaapanaApi.route("/api/abort", methods=["POST"])
def abort_dag_runs():
    """
    This API endpoint aborts multiple DAG runs based on a list of run_ids.
    """
    data = request.get_json(force=True)
    run_ids = data.get("run_ids", [])
    if not run_ids:
        return jsonify({"error": "No run_ids provided"}), 400

    session = settings.Session()
    try:
        # Fetch all relevant DAG runs
        dag_runs = session.query(DagRun).filter(DagRun.run_id.in_(run_ids)).all()
        if not dag_runs:
            return jsonify({"error": "No matching DAG runs found"}), 404

        dag_ids = {dag_run.dag_id for dag_run in dag_runs}

        # Bulk update DAG run states
        session.query(DagRun).filter(DagRun.run_id.in_(run_ids)).update(
            {DagRun.state: DagRunState.FAILED, DagRun.end_date: timezone.utcnow()},
            synchronize_session=False,
        )

        # Fetch all relevant TaskInstances
        task_instances = (
            session.query(TaskInstance)
            .filter(
                TaskInstance.dag_id.in_(dag_ids),
                TaskInstance.run_id.in_(run_ids),
            )
            .all()
        )

        # Bulk update TaskInstance states
        for task_instance in task_instances:
            if task_instance.state == TaskInstanceState.RUNNING:
                task_instance.state = TaskInstanceState.FAILED
            elif task_instance.state not in [
                TaskInstanceState.SUCCESS,
                TaskInstanceState.FAILED,
                TaskInstanceState.RUNNING,
            ]:
                task_instance.state = TaskInstanceState.FAILED
            elif task_instance.state is None:
                task_instance.state = TaskInstanceState.FAILED

        session.bulk_save_objects(task_instances)
        session.commit()

        return jsonify({"message": f"Aborted DAG runs: {run_ids}"}), 200

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@kaapanaApi.route("/api/getdagruns", methods=["POST"])
@csrf.exempt
def getAllDagRuns():
    data = request.get_json(force=True)
    dag_id = data["dag_id"] if "dag_id" in data else None
    run_id = data["run_id"] if "run_id" in data else None
    state = data["state"] if "state" in data else None
    limit = data["limit"] if "limit" in data else None
    count = data["count"] if "count" in data else None
    categorize = data["categorize"] if "categorize" in data else None

    session = settings.Session()
    time_format = "%Y-%m-%dT%H:%M:%S"

    try:
        all_dagruns = session.query(DagRun)
        if dag_id is not None:
            all_dagruns = all_dagruns.filter(DagRun.dag_id == dag_id)

        if run_id is not None:
            all_dagruns = all_dagruns.filter(DagRun.run_id == run_id)

        if state is not None:
            all_dagruns = all_dagruns.filter(DagRun.state == state)

        all_dagruns = list(all_dagruns.order_by(DagRun.execution_date).all())

        if limit is not None:
            all_dagruns = all_dagruns[: int(limit)]

        dagruns = []
        for dagrun in all_dagruns:
            conf = dagrun.conf
            if conf is not None and "user_public_id" in conf:
                user = conf["user_public_id"]
            else:
                user = "0000-0000-0000-0000-0000"

            dagruns.append(
                {
                    "user": user,
                    "dag_id": dagrun.dag_id,
                    "run_id": dagrun.run_id,
                    "state": dagrun.state,
                    "execution_time": dagrun.execution_date,
                }
            )

        if count is not None:
            dagruns = len(all_dagruns)

    except NoResultFound:
        print("No Dags found!")
        return jsonify({})

    return jsonify(dagruns)


@kaapanaApi.route("/api/getdags", methods=["GET"])
@csrf.exempt
def get_dags_endpoint():
    with app.app_context():
        app.json.sort_keys = False
    ids_only = request.args.get("ids_only")
    active_only = request.args.get("active_only")
    session = settings.Session()

    dag_objects = DagBag().dags
    dags = {}

    all_dags = list(session.query(DagModel).all())

    for dag_obj in all_dags:
        dag_dict = dag_obj.__dict__

        if active_only is not None and not dag_dict["is_active"]:
            continue

        dag_id = dag_dict["dag_id"]
        if (
            dag_id in dag_objects
            and dag_objects[dag_id] is not None
            and hasattr(dag_objects[dag_id], "default_args")
        ):
            default_args = dag_objects[dag_id].default_args
            for default_arg in default_args.keys():
                if default_arg[:3] == "ui_":
                    dag_dict[default_arg] = default_args[default_arg]

        del dag_dict["_sa_instance_state"]

        dags[dag_id] = parse_ui_dict(dag_dict)

    return jsonify(dags)


def check_dag_exists(session, dag_id):
    """
    if returns an error response, if it doesn't exist
    """
    dag_exists = session.query(DagModel).filter(DagModel.dag_id == dag_id).count()
    if not dag_exists:
        return Response("Dag {} does not exist".format(dag_id), HTTPStatus.BAD_REQUEST)

    return None


@kaapanaApi.route("/api/dagids/<dag_id>", methods=["GET"])
@csrf.exempt
def get_dag_runs(dag_id):
    """
    .. http:get:: /trigger/<dag_id>
        Get the run_ids for a dag_id, ordered by execution date
        **Example request**:
        .. sourcecode:: http
            GET /trigger/make_fit
            Host: localhost:7357
        **Example response**:
        .. sourcecode:: http
            HTTP/1.1 200 OK
            Content-Type: application/json
            {
              "dag_id": "daily_processing",
              "run_ids": ["my_special_run", "normal_run_17"]
            }
    """
    session = settings.Session()

    error_response = check_dag_exists(session, dag_id)
    if error_response:
        return error_response

    dag_runs = (
        session.query(DagRun)
        .filter(DagRun.dag_id == dag_id)
        .order_by(DagRun.execution_date)
        .all()
    )
    run_ids = [dag_run.run_id for dag_run in dag_runs]

    return jsonify(dag_id=dag_id, run_ids=run_ids)


@kaapanaApi.route("/api/dags/<dag_id>/dagRuns/state/<state>/count", methods=["GET"])
@csrf.exempt
def get_num_dag_runs_by_state(dag_id, state):
    """
    The old api /api/experimental/dags/<dag_id>/dag_runs?state=running has been replaced by
    /api/v1/dags/<dag_id>/dagRuns where filtering via state is not possible anymore.
    this endpoint is directly retuning the needed info for the CTP.
    """
    session = settings.Session()
    query = session.query(DagRun)
    state = state.lower() if state else None
    query = query.filter(DagRun.dag_id == dag_id, DagRun.state == state)
    number_of_dagruns = query.count()
    return jsonify(number_of_dagruns=number_of_dagruns)


@kaapanaApi.route("/api/dagdetails", methods=["POST"])
@csrf.exempt
def dag_run_status_batch():
    """
    This API endpoint returns the status of multiple DAG runs based on a list of run_ids.
    """
    data = request.get_json(force=True)
    run_ids = data.get("run_ids", [])
    if not run_ids:
        return jsonify({"error": "No run_ids provided"}), 400

    session = settings.Session()
    results = {}
    time_format = "%Y-%m-%dT%H:%M:%S"

    try:
        dag_runs = session.query(DagRun).filter(DagRun.run_id.in_(run_ids)).all()

        if not dag_runs:
            return jsonify({"error": "No matching DAG runs found"}), 404

        for dag_run in dag_runs:
            results[dag_run.run_id] = {
                "dag_id": dag_run.dag_id,
                "state": dag_run.state,
                "execution_date": dag_run.execution_date.strftime(time_format),
            }

        # Identify any missing run_ids
        found_run_ids = {dag_run.run_id for dag_run in dag_runs}
        missing_run_ids = set(run_ids) - found_run_ids
        if missing_run_ids:
            return (
                jsonify(
                    {
                        "error": f"RunIds {missing_run_ids} do not exist",
                        "results": results,
                    }
                ),
                HTTPStatus.PARTIAL_CONTENT,
            )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

    return jsonify(results)
