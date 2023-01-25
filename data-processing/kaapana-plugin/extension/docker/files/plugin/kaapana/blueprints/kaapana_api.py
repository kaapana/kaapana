from flask import g, Blueprint, request, jsonify, Response, url_for
from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound
from datetime import datetime
import airflow.api
from http import HTTPStatus
from airflow.exceptions import AirflowException
from airflow.models import DagRun, DagModel, DAG, DagBag
from airflow.models.taskinstance import TaskInstance
from airflow import settings
from airflow.utils import timezone
from airflow.utils.state import State, TaskInstanceState, DagRunState
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.www.app import csrf
import json
import time
from kaapana.blueprints.kaapana_utils import generate_run_id, generate_minio_credentials, parse_ui_dict
from airflow.api.common.trigger_dag import trigger_dag as trigger
from airflow.api.common.experimental.mark_tasks import set_dag_run_state_to_failed as set_dag_run_failed
from airflow.api.common.experimental.mark_tasks import get_execution_dates, find_task_relatives, verify_dag_run_integrity, get_subdag_runs, get_all_dag_task_query, all_subdag_tasks_query
from kaapana.operators.HelperOpensearch import HelperOpensearch
from kaapana.blueprints.kaapana_utils import generate_run_id, generate_minio_credentials, parse_ui_dict
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
from airflow.api.common.trigger_dag import trigger_dag as trigger
from flask import current_app as app

_log = LoggingMixin().log
parallel_processes = 1
"""
Represents a blueprint kaapanaApi
"""
kaapanaApi = Blueprint('kaapana', __name__, url_prefix='/kaapana')

@csrf.exempt
@kaapanaApi.route('/api/trigger/<string:dag_id>', methods=['POST'])
def trigger_dag(dag_id):
    #headers = dict(request.headers)
    data = request.get_json(force=True)
    print(f"data: {data}")
    #username = headers["X-Forwarded-Preferred-Username"] if "X-Forwarded-Preferred-Username" in headers else "unknown"
    if 'conf' in data:
        tmp_conf = data['conf']
    else:
        tmp_conf = data

    # For authentication
    if "x_auth_token" in data:
        tmp_conf["x_auth_token"] = data["x_auth_token"]
    else:
        tmp_conf["x_auth_token"] = request.headers.get('X-Auth-Token')

    ################################################################################################
    #### Deprecated! Will be removed with the next version 0.1.3

    if "workflow_form" in tmp_conf: # in the future only workflow_form should be included in the tmp_conf
        tmp_conf["form_data"] = tmp_conf["workflow_form"]
    elif "form_data" in tmp_conf:
        tmp_conf["workflow_form"] = tmp_conf["form_data"]

    ################################################################################################

    run_id = generate_run_id(dag_id)

    print(json.dumps(tmp_conf, indent=2))

    execution_date = None
    try:
        dr = trigger(dag_id, run_id, tmp_conf, execution_date, replace_microseconds=False)
    except AirflowException as err:
        _log.error(err)
        response = jsonify(error="{}".format(err))
        response.status_code = err.status_code
        return response

    message = ["{} created!".format(dr.dag_id)]
    response = jsonify(message=message)
    return response

@csrf.exempt
@kaapanaApi.route('/api/get_dagrun_tasks/<dag_id>/<run_id>', methods=['POST'])
def get_dagrun_tasks(dag_id, run_id):
    '''
    This Airflow API does the following:
    - query from airflow a dag_run by dag_id and run_id
    - get all tasks including their states of queried dag_run
    - return tasks
    '''
    #headers = dict(request.headers)
    data = request.get_json(force=True)
    print(f"data: {data}")
    #username = headers["X-Forwarded-Preferred-Username"] if "X-Forwarded-Preferred-Username" in headers else "unknown"
    if 'conf' in data:
        tmp_conf = data['conf']
    else:
        tmp_conf = data
    # For authentication
    if "x_auth_token" in data:
        tmp_conf["x_auth_token"] = data["x_auth_token"]
    else:
        tmp_conf["x_auth_token"] = request.headers.get('X-Auth-Token')
    ################################################################################################ 
    #### Deprecated! Will be removed with the next version 0.1.3
    if "workflow_form" in tmp_conf: # in the future only workflow_form should be included in the tmp_conf
        tmp_conf["form_data"] = tmp_conf["workflow_form"]
    elif "form_data" in tmp_conf:
        tmp_conf["workflow_form"] = tmp_conf["form_data"]
    ################################################################################################

    ### actual start of function ###
    dag_objects = DagBag().dags                 # returns all DAGs available on platform
    desired_dag = dag_objects[dag_id]           # filter desired_dag from all available dags via dag_id
    session = settings.Session()
    message = []

    task_ids = [task.task_id for task in desired_dag.tasks]  # get task_ids of desired_dag
    tis = session.query(TaskInstance).filter(                # query TaskInstances which are part of desired_dag wit run_id=run_id and task_ids
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
    message.append(f'{state_dict}')
    message.append(f'{exdate_dict}')
    response = jsonify(message=message)
    return response



@csrf.exempt
@kaapanaApi.route('/api/abort/<dag_id>/<run_id>', methods=['POST'])
def abort_dag_run(dag_id, run_id):
    #headers = dict(request.headers)
    data = request.get_json(force=True)
    print(f"data: {data}")

    #username = headers["X-Forwarded-Preferred-Username"] if "X-Forwarded-Preferred-Username" in headers else "unknown"
    if 'conf' in data:
        tmp_conf = data['conf']
    else:
        tmp_conf = data

    # For authentication
    if "x_auth_token" in data:
        tmp_conf["x_auth_token"] = data["x_auth_token"]
    else:
        tmp_conf["x_auth_token"] = request.headers.get('X-Auth-Token')

    ################################################################################################ 
    #### Deprecated! Will be removed with the next version 0.1.3

    if "workflow_form" in tmp_conf: # in the future only workflow_form should be included in the tmp_conf
        tmp_conf["form_data"] = tmp_conf["workflow_form"]
    elif "form_data" in tmp_conf:
        tmp_conf["workflow_form"] = tmp_conf["form_data"]
    
    ################################################################################################ 

    # abort dag_run by executing set_dag_run_state_to_failed() (source: https://github.com/apache/airflow/blob/main/airflow/api/common/mark_tasks.py#L421)
    dag_objects = DagBag().dags                 # returns all DAGs available on platform
    desired_dag = dag_objects[dag_id]           # filter desired_dag from all available dags via dag_id

    session = settings.Session()
    dag_runs_of_desired_dag = session.query(DagRun).filter(DagRun.dag_id == desired_dag.dag_id)
    for dag_run_of_desired_dag in dag_runs_of_desired_dag:
        if dag_run_of_desired_dag.run_id == run_id:
            desired_execution_date = dag_run_of_desired_dag.execution_date
            break
        else:
            desired_execution_date = None

    message = []

    # Own solution highly inspred by airflow latest (2.4.3) -> def set_dag_run_state_to_failed(*, dag: DAG, execution_date: datetime | None = None, run_id: str | None = None, commit: bool = False, session: SASession = NEW_SESSION,)
    dag = desired_dag
    execution_date = desired_execution_date
    run_id = run_id
    commit = True
    session = session
    state = TaskInstanceState.FAILED
    
    if not dag:
        return []
    if execution_date:
        if not timezone.is_localized(execution_date):
            raise ValueError(f"Received non-localized date {execution_date}")
        dag_run = dag.get_dagrun(execution_date=execution_date)
        if not dag_run:
            raise ValueError(f"DagRun with execution_date: {execution_date} not found")
        run_id = dag_run.run_id
    if not run_id:
        raise ValueError(f"Invalid dag_run_id: {run_id}")

    # Mark the dag run to failed.
    if commit:
        # _set_dag_run_state(dag.dag_id, run_id, DagRunState.FAILED, session)
        # definition: def _set_dag_run_state(dag_id: str, run_id: str, state: DagRunState, session: SASession = NEW_SESSION)
        dag_run_state = DagRunState.FAILED
        dag_run = session.query(DagRun).filter(DagRun.dag_id == dag_id, DagRun.run_id == run_id).one()
        dag_run.state = dag_run_state
        if dag_run_state == State.RUNNING:
            dag_run.start_date = timezone.utcnow()
            dag_run.end_date = None
        else:
            dag_run.end_date = timezone.utcnow()
        session.merge(dag_run)
    
    # Mark only RUNNING task instances.
    task_ids = [task.task_id for task in dag.tasks]
    tis_r = session.query(TaskInstance).filter(
        TaskInstance.dag_id == dag.dag_id,
        TaskInstance.run_id == run_id,
        TaskInstance.task_id.in_(task_ids),
        TaskInstance.state == (TaskInstanceState.RUNNING),
    )
    tis_r = [ti for ti in tis_r]
    if commit:
        for ti in tis_r:
            message.append(f"Running Task {ti} and its state {ti.state}")
            ti.set_state(State.FAILED) # set non-running and not finished tasks to skipped

    # Mark non-finished and not running tasks as SKIPPED.
    tis = session.query(TaskInstance).filter(
        TaskInstance.dag_id == dag.dag_id,
        TaskInstance.run_id == run_id,
        TaskInstance.state != (TaskInstanceState.SUCCESS),
        TaskInstance.state != (TaskInstanceState.RUNNING),
        TaskInstance.state != (TaskInstanceState.FAILED),
    )
    tis = [ti for ti in tis]
    if commit:
        for ti in tis:
            message.append(f"Non-finished Task {ti} and its state {ti.state}")
            ti.set_state(State.SKIPPED) # set non-running and not finished tasks to skipped
    
    # Mark tasks in state None as SKIPPED
    tis_n = session.query(TaskInstance).filter(
        TaskInstance.dag_id == dag.dag_id,
        TaskInstance.run_id == run_id,
        TaskInstance.state == None,
    )
    tis_n = [ti for ti in tis_n]
    if commit:
        for ti in tis_n:
            message.append(f"None-state Task {ti} and its state {ti.state}")
            ti.set_state(State.SKIPPED) # set None-state tasks to skipped

    # if no task is marked as FAILED so far, take last task marked as SUCCESS and set it to FAILED --> such that whole dag_run is also marked as failed!
    # query tasks for failed
    tis_f = session.query(TaskInstance).filter(
        TaskInstance.dag_id == dag.dag_id,
        TaskInstance.run_id == run_id,
        TaskInstance.state == (TaskInstanceState.FAILED),
    )
    tis_f = [ti for ti in tis_f]
    message.append(f"So far FAILED tasks: {tis_f}")
    if len(tis_f) == 0:    
        # if no failed task found -> query tasks for succes; select last succeeded task and set is to failed
        tis_s = session.query(TaskInstance).filter(
            TaskInstance.dag_id == dag.dag_id,
            TaskInstance.run_id == run_id,
            TaskInstance.state == (TaskInstanceState.SUCCESS),
        )
        message.append(f"tis_s: {tis_s}")
        latest_ti_s = tis_s.order_by(TaskInstance.start_date.desc()).first()
        message.append(f"So far SUCCESS task, to.be changed to FAILED: {latest_ti_s}")
        latest_ti_s.set_state(State.FAILED)
    
    all_tis = [tis_r, tis, tis_n]

    message.append(f"Result of Job abortion: {all_tis}")
    response = jsonify(message=message)
    return response


@kaapanaApi.route('/api/getdagruns', methods=['GET'])
@csrf.exempt
def getAllDagRuns():
    dag_id = request.args.get('dag_id')
    run_id = request.args.get('run_id')
    state = request.args.get('state')
    limit = request.args.get('limit')
    count = request.args.get('count')
    categorize = request.args.get('categorize')

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
            all_dagruns = all_dagruns[:int(limit)]

        dagruns = []
        for dagrun in all_dagruns:

            conf = dagrun.conf
            if conf is not None and "user_public_id" in conf:
                user = conf["user_public_id"]
            else:
                user = "0000-0000-0000-0000-0000"

            dagruns.append({
                'user': user,
                'dag_id': dagrun.dag_id,
                'run_id': dagrun.run_id,
                'state': dagrun.state,
                'execution_time': dagrun.execution_date
            })

        if count is not None:
            dagruns = len(all_dagruns)

    except NoResultFound:
        print('No Dags found!')
        return jsonify({})

    return jsonify(dagruns)


@kaapanaApi.route('/api/getdags', methods=['GET'])
@csrf.exempt
def get_dags_endpoint():
    ids_only = request.args.get('ids_only')
    active_only = request.args.get('active_only')
    session = settings.Session()

    dag_objects = DagBag().dags
    dags = {}

    all_dags = list(session.query(DagModel).all())

    for dag_obj in all_dags:
        dag_dict = dag_obj.__dict__

        if active_only is not None and not dag_dict["is_active"]:
            continue

        dag_id = dag_dict['dag_id']
        if dag_id in dag_objects and dag_objects[dag_id] is not None and hasattr(dag_objects[dag_id], 'default_args'):
            default_args = dag_objects[dag_id].default_args
            for default_arg in default_args.keys():
                if default_arg[:3] == "ui_":
                    dag_dict[default_arg] = default_args[default_arg]

        del dag_dict['_sa_instance_state']

        dags[dag_id] = parse_ui_dict(dag_dict)

    app.config['JSON_SORT_KEYS'] = False
    return jsonify(dags)


def check_dag_exists(session, dag_id):
    """
    if returns an error response, if it doesn't exist
    """
    dag_exists = session.query(DagModel).filter(
        DagModel.dag_id == dag_id).count()
    if not dag_exists:
        return Response('Dag {} does not exist'.format(dag_id), HTTPStatus.BAD_REQUEST)

    return None


@kaapanaApi.route('/api/dagids/<dag_id>', methods=['GET'])
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

    dag_runs = session.query(DagRun).filter(
        DagRun.dag_id == dag_id).order_by(DagRun.execution_date).all()
    run_ids = [dag_run.run_id for dag_run in dag_runs]

    return jsonify(dag_id=dag_id, run_ids=run_ids)


@kaapanaApi.route('/api/dags/<dag_id>/dagRuns/state/<state>/count', methods=['GET'])
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


@kaapanaApi.route('/api/dagdetails/<dag_id>/<run_id>', methods=['GET'])
@csrf.exempt
def dag_run_status(dag_id, run_id):
    session = settings.Session()

    error_response = check_dag_exists(session, dag_id)
    if error_response:
        return error_response

    try:
        dag_run = session.query(DagRun).filter(
            and_(DagRun.dag_id == dag_id, DagRun.run_id == run_id)).one()
    except NoResultFound:
        return Response('RunId {} does not exist for Dag {}'.format(run_id, dag_id), HTTPStatus.BAD_REQUEST)

    time_format = "%Y-%m-%dT%H:%M:%S"
    return jsonify(
        dag_id=dag_id,
        run_id=run_id,
        state=dag_run.state,
        execution_date=dag_run.execution_date.strftime(time_format)
    )


# Should be all moved to kaapana backend!!
# Authorization topics
@kaapanaApi.route('/api/getaccesstoken')
@csrf.exempt
def get_access_token():
    x_auth_token = request.headers.get('X-Forwarded-Access-Token')
    if x_auth_token is None:
        return jsonify({'message': 'No X-Auth-Token found in your request, seems that you are calling me from the backend!'}), 404
    return jsonify(xAuthToken=x_auth_token)


@kaapanaApi.route('/api/getminiocredentials')
@csrf.exempt
def get_minio_credentials():
    x_auth_token = request.headers.get('X-Forwarded-Access-Token')
    access_key, secret_key, session_token = generate_minio_credentials(x_auth_token)
    return jsonify({'accessKey': access_key, 'secretKey': secret_key, 'sessionToken': session_token}), 200

@kaapanaApi.route('/api/get-os-dashboards')
@csrf.exempt
def get_os_dashboards():
    try:
        res = HelperOpensearch.os_client.search(body={
            "query": {
                "exists": {
                    "field": "dashboard"
                }
            },
            "_source": ["dashboard.title"]
        }, size=10000, from_=0)
    except Exception as e:
        print("ERROR in OpenSearch search!")
        return jsonify({'Error message': e}), 500

    hits = res['hits']['hits']
    dashboards = list(sorted([ hit['_source']['dashboard']['title'] for hit in hits ]))
    return jsonify({'dashboards': dashboards}), 200


@kaapanaApi.route('/api/get-static-website-results')
@csrf.exempt
def get_static_website_results():
    import uuid
    import os
    from minio import Minio

    def build_tree(item, filepath, org_filepath):
        # Adapted from https://stackoverflow.com/questions/8484943/construct-a-tree-from-list-os-file-paths-python-performance-dependent
        splits = filepath.split('/', 1)
        if len(splits) == 1:
            print(splits)
            # item.update({
            #     "name": splits[0]
            #     # "file": "html",
            # })
            # if "vuetifyItems" not in item:
            #     item["vuetifyItems"] = []
            item["vuetifyFiles"].append({
                "name": splits[0],
                "file": "html",
                "path": f"/static-website-browser/{org_filepath}"
            })
        else:
            parent_folder, filepath = splits
            if parent_folder not in item:
                item[parent_folder] = {"vuetifyFiles": []}
            build_tree(item[parent_folder], filepath, org_filepath)

    def get_vuetify_tree_structure(tree):
        subtree = []
        for parent, children in tree.items():
            print(parent, children)
            if parent == 'vuetifyFiles':
                subtree = children
            else:
                subtree.append({
                    'name': parent,
                    'path': str(uuid.uuid4()),
                    'children': get_vuetify_tree_structure(children)
                })
        return subtree

    _minio_host='minio-service.store.svc'
    _minio_port='9000'
    minioClient = Minio(_minio_host+":"+_minio_port,
                        access_key='kaapanaminio',
                        secret_key='Kaapana2020',
                        secure=False)


    tree = {"vuetifyFiles": []}
    objects = minioClient.list_objects("staticwebsiteresults", prefix=None, recursive=True)
    for obj in objects:
        if obj.object_name.endswith('html') and obj.object_name != 'index.html':
            build_tree(tree, obj.object_name, obj.object_name)
    return jsonify(get_vuetify_tree_structure(tree)), 200
import warnings
from flask import g, Blueprint, request, jsonify, Response, url_for
from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound
from datetime import datetime
import airflow.api
from http import HTTPStatus
from airflow.exceptions import AirflowException
from airflow.models import DagRun, DagModel, DAG, DagBag
from airflow import settings
from airflow.utils import timezone
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.www.app import csrf
import json
from kaapana.operators.HelperOpensearch import HelperOpensearch
from kaapana.blueprints.kaapana_utils import generate_run_id, generate_minio_credentials, parse_ui_dict
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
from airflow.api.common.trigger_dag import trigger_dag as trigger
from flask import current_app as app

_log = LoggingMixin().log
parallel_processes = 1
"""
Represents a blueprint kaapanaApi
"""
kaapanaApi = Blueprint('kaapana', __name__, url_prefix='/kaapana')

@csrf.exempt
@kaapanaApi.route('/api/trigger/<string:dag_id>', methods=['POST'])
def trigger_dag(dag_id):
    #headers = dict(request.headers)
    data = request.get_json(force=True)
    #username = headers["X-Forwarded-Preferred-Username"] if "X-Forwarded-Preferred-Username" in headers else "unknown"
    if 'conf' in data:
        tmp_conf = data['conf']
    else:
        tmp_conf = data

    # For authentication
    if "x_auth_token" in data:
        tmp_conf["x_auth_token"] = data["x_auth_token"]
    else:
        tmp_conf["x_auth_token"] = request.headers.get('X-Auth-Token')

    ################################################################################################
    #### Deprecated! Will be removed with the next version 0.1.3

    if "workflow_form" in tmp_conf: # in the future only workflow_form should be included in the tmp_conf
        tmp_conf["form_data"] = tmp_conf["workflow_form"]
    elif "form_data" in tmp_conf:
        tmp_conf["workflow_form"] = tmp_conf["form_data"]

    ################################################################################################

    run_id = generate_run_id(dag_id)

    print(json.dumps(tmp_conf, indent=2))

    execution_date = None
    try:
        dr = trigger(dag_id, run_id, tmp_conf, execution_date, replace_microseconds=False)
    except AirflowException as err:
        _log.error(err)
        response = jsonify(error="{}".format(err))
        response.status_code = err.status_code
        return response

    message = ["{} created!".format(dr.dag_id)]
    response = jsonify(message=message)
    return response


@kaapanaApi.route('/api/getdagruns', methods=['GET'])
@csrf.exempt
def getAllDagRuns():
    dag_id = request.args.get('dag_id')
    run_id = request.args.get('run_id')
    state = request.args.get('state')
    limit = request.args.get('limit')
    count = request.args.get('count')
    categorize = request.args.get('categorize')

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
            all_dagruns = all_dagruns[:int(limit)]

        dagruns = []
        for dagrun in all_dagruns:

            conf = dagrun.conf
            if conf is not None and "user_public_id" in conf:
                user = conf["user_public_id"]
            else:
                user = "0000-0000-0000-0000-0000"

            dagruns.append({
                'user': user,
                'dag_id': dagrun.dag_id,
                'run_id': dagrun.run_id,
                'state': dagrun.state,
                'execution_time': dagrun.execution_date
            })

        if count is not None:
            dagruns = len(all_dagruns)

    except NoResultFound:
        print('No Dags found!')
        return jsonify({})

    return jsonify(dagruns)


@kaapanaApi.route('/api/getdags', methods=['GET'])
@csrf.exempt
def get_dags_endpoint():
    ids_only = request.args.get('ids_only')
    active_only = request.args.get('active_only')
    session = settings.Session()

    dag_objects = DagBag().dags
    dags = {}

    all_dags = list(session.query(DagModel).all())

    for dag_obj in all_dags:
        dag_dict = dag_obj.__dict__

        if active_only is not None and not dag_dict["is_active"]:
            continue

        dag_id = dag_dict['dag_id']
        if dag_id in dag_objects and dag_objects[dag_id] is not None and hasattr(dag_objects[dag_id], 'default_args'):
            default_args = dag_objects[dag_id].default_args
            for default_arg in default_args.keys():
                if default_arg[:3] == "ui_":
                    dag_dict[default_arg] = default_args[default_arg]

        del dag_dict['_sa_instance_state']

        dags[dag_id] = parse_ui_dict(dag_dict)

    app.config['JSON_SORT_KEYS'] = False
    return jsonify(dags)


def check_dag_exists(session, dag_id):
    """
    if returns an error response, if it doesn't exist
    """
    dag_exists = session.query(DagModel).filter(
        DagModel.dag_id == dag_id).count()
    if not dag_exists:
        return Response('Dag {} does not exist'.format(dag_id), HTTPStatus.BAD_REQUEST)

    return None


@kaapanaApi.route('/api/dagids/<dag_id>', methods=['GET'])
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

    dag_runs = session.query(DagRun).filter(
        DagRun.dag_id == dag_id).order_by(DagRun.execution_date).all()
    run_ids = [dag_run.run_id for dag_run in dag_runs]

    return jsonify(dag_id=dag_id, run_ids=run_ids)


@kaapanaApi.route('/api/dags/<dag_id>/dagRuns/state/<state>/count', methods=['GET'])
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


@kaapanaApi.route('/api/dagdetails/<dag_id>/<run_id>', methods=['GET'])
@csrf.exempt
def dag_run_status(dag_id, run_id):
    session = settings.Session()

    error_response = check_dag_exists(session, dag_id)
    if error_response:
        return error_response

    try:
        dag_run = session.query(DagRun).filter(
            and_(DagRun.dag_id == dag_id, DagRun.run_id == run_id)).one()
    except NoResultFound:
        return Response('RunId {} does not exist for Dag {}'.format(run_id, dag_id), HTTPStatus.BAD_REQUEST)

    time_format = "%Y-%m-%dT%H:%M:%S"
    return jsonify(
        dag_id=dag_id,
        run_id=run_id,
        state=dag_run.state,
        execution_date=dag_run.execution_date.strftime(time_format)
    )


# Should be all moved to kaapana backend!!
# Authorization topics
@kaapanaApi.route('/api/getaccesstoken')
@csrf.exempt
def get_access_token():
    x_auth_token = request.headers.get('X-Forwarded-Access-Token')
    if x_auth_token is None:
        return jsonify({'message': 'No X-Auth-Token found in your request, seems that you are calling me from the backend!'}), 404
    return jsonify(xAuthToken=x_auth_token)


@kaapanaApi.route('/api/getminiocredentials')
@csrf.exempt
def get_minio_credentials():
    x_auth_token = request.headers.get('X-Forwarded-Access-Token')
    access_key, secret_key, session_token = generate_minio_credentials(x_auth_token)
    return jsonify({'accessKey': access_key, 'secretKey': secret_key, 'sessionToken': session_token}), 200

@kaapanaApi.route('/api/get-os-dashboards')
@csrf.exempt
def get_os_dashboards():
    try:
        res = HelperOpensearch.os_client.search(body={
            "query": {
                "exists": {
                    "field": "dashboard"
                }
            },
            "_source": ["dashboard.title"]
        }, size=10000, from_=0)
    except Exception as e:
        print("ERROR in OpenSearch search!")
        return jsonify({'Error message': e}), 500

    hits = res['hits']['hits']
    dashboards = list(sorted([ hit['_source']['dashboard']['title'] for hit in hits ]))
    return jsonify({'dashboards': dashboards}), 200


@kaapanaApi.route('/api/get-static-website-results')
@csrf.exempt
def get_static_website_results():
    import uuid
    import os
    from minio import Minio

    def build_tree(item, filepath, org_filepath):
        # Adapted from https://stackoverflow.com/questions/8484943/construct-a-tree-from-list-os-file-paths-python-performance-dependent
        splits = filepath.split('/', 1)
        if len(splits) == 1:
            print(splits)
            # item.update({
            #     "name": splits[0]
            #     # "file": "html",
            # })
            # if "vuetifyItems" not in item:
            #     item["vuetifyItems"] = []
            item["vuetifyFiles"].append({
                "name": splits[0],
                "file": "html",
                "path": f"/static-website-browser/{org_filepath}"
            })
        else:
            parent_folder, filepath = splits
            if parent_folder not in item:
                item[parent_folder] = {"vuetifyFiles": []}
            build_tree(item[parent_folder], filepath, org_filepath)

    def get_vuetify_tree_structure(tree):
        subtree = []
        for parent, children in tree.items():
            print(parent, children)
            if parent == 'vuetifyFiles':
                subtree = children
            else:
                subtree.append({
                    'name': parent,
                    'path': str(uuid.uuid4()),
                    'children': get_vuetify_tree_structure(children)
                })
        return subtree

    _minio_host=f'minio-service.{SERVICES_NAMESPACE}.svc'
    _minio_port='9000'
    minioClient = Minio(_minio_host+":"+_minio_port,
                        access_key='kaapanaminio',
                        secret_key='Kaapana2020',
                        secure=False)


    tree = {"vuetifyFiles": []}
    objects = minioClient.list_objects("staticwebsiteresults", prefix=None, recursive=True)
    for obj in objects:
        if obj.object_name.endswith('html') and obj.object_name != 'index.html':
            build_tree(tree, obj.object_name, obj.object_name)
    return jsonify(get_vuetify_tree_structure(tree)), 200



# TODO: Use tagging operator
@csrf.exempt
@kaapanaApi.route('/api/tag', methods=['POST'])
def tag_data():
    from typing import List

    def tagging(series_instance_uid: str, tags: List[str],
                tags2add: List[str] = [], tags2delete: List[str] = []):
        print(series_instance_uid)
        print(f"Tags 2 add: {tags2add}")
        print(f"Tags 2 delete: {tags2delete}")

        # Read Tags
        es = HelperOpensearch.os_client
        doc = es.get(index="meta-index", id=series_instance_uid)
        print(doc)
        index_tags = doc["_source"].get("dataset_tags_keyword", [])

        final_tags = list(
            set(tags).union(set(index_tags)).difference(set(tags2delete)).union(
                set(tags2add)))
        print(f"Final tags: {final_tags}")

        # Write Tags back
        body = {"doc": {"dataset_tags_keyword": final_tags}}
        es.update(index="meta-index", id=series_instance_uid, body=body)

    try:
        data = request.get_json(force=True)
        for series in data:
            tagging(
                series["series_instance_uid"], series['tags'],
                series['tags2add'], series["tags2delete"]
            )
        return jsonify({}), 200

    except Exception as e:
        print("ERROR!")
        return jsonify({'Error message': e}), 500


@kaapanaApi.route('/api/curation_tool/structured', methods=['POST'])
@csrf.exempt
def get_query_elastic_structured():
    query = request.get_json(force=True)
    if not query:
        query = {"query_string": {"query": "*"}}


    try:
        res = HelperOpensearch.os_client.search(body={
            "size": 0,
            "query": query,
            "aggs": {
                "Patients": {
                    "terms": {
                        "field": "00100020 PatientID_keyword.keyword",
                        "size": 10000
                    },
                    "aggs": {
                        "Modalities": {
                            "terms": {
                                "field": "00080060 Modality_keyword.keyword"
                            }
                        },
                        "Studies": {
                            "terms": {
                                "field": "0020000D StudyInstanceUID_keyword.keyword",
                                "size": 10000
                            },
                            "aggs": {
                                "Series": {
                                    "top_hits": {
                                        "size": 100,
                                        "_source": {
                                            "includes": [
                                                "00100020 PatientID_keyword",
                                                "00100040 PatientSex_keyword",
                                                "00101010 PatientAge_integer",
                                                "00082218 AnatomicRegionSequence_object_object.00080104 CodeMeaning_keyword",
                                                "0020000D StudyInstanceUID_keyword",
                                                "0020000E SeriesInstanceUID_keyword",
                                                "00080018 SOPInstanceUID_keyword",
                                                "00080060 Modality_keyword",
                                                "00081030 StudyDescription_keyword",
                                                "0008103E SeriesDescription_keyword",
                                                "00100010 PatientName_keyword_alphabetic",
                                                "00181030 ProtocolName_keyword",
                                                "00180050 SliceThickness_float",
                                                "00080021 SeriesDate_date",
                                                "00080020 StudyDate_date",
                                                "00200011 SeriesNumber_integer",
                                                "dataset_tags_keyword"
                                            ]
                                        },
                                        "sort": [
                                            {
                                                "00080020 StudyDate_date": {
                                                    "order": "desc"
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    }
                }
            }
        })
    except Exception as e:
        print("ERROR in elasticsearch search!")
        return jsonify({'Error message': e}), 500

    results = list()

    for patient in res['aggregations']['Patients']['buckets']:
        patient_dict = dict(
            patient_key=patient['key'],
            study_count=patient['doc_count'],
            modalities=[m['key'] for m in patient['Modalities']['buckets']],
            studies=[]
        )
        for study in patient['Studies']['buckets']:
            study_dict = dict(
                study_key=study['key'],
                series_count=study['doc_count'],
                series=[]
            )
            for i, series in enumerate(study['Series']['hits']['hits']):
                study_dict['series'].append(series['_source'])
                if i == 0:
                    # Patient params
                    if '00101010 PatientAge_integer' in series[
                        '_source'].keys():
                        patient_dict['00101010 PatientAge_integer'] = \
                            series['_source']['00101010 PatientAge_integer']
                    if '00100010 PatientName_keyword_alphabetic' in series[
                        '_source'].keys():
                        patient_dict[
                            '00100010 PatientName_keyword_alphabetic'] = \
                            series['_source'][
                                '00100010 PatientName_keyword_alphabetic']
                    if '00100040 PatientSex_keyword' in series[
                        '_source'].keys():
                        patient_dict['00100040 PatientSex_keyword'] = \
                            series['_source']['00100040 PatientSex_keyword']
                    # Study params
                    if '00081030 StudyDescription_keyword' in series[
                        '_source'].keys():
                        study_dict['00081030 StudyDescription_keyword'] = \
                            series['_source'][
                                '00081030 StudyDescription_keyword']
                    if '00080020 StudyDate_date' in series['_source'].keys():
                        study_dict['00080020 StudyDate_date'] = \
                            series['_source']['00080020 StudyDate_date']
            patient_dict['studies'].append(study_dict)
        results.append(patient_dict)
    return jsonify(results), 200

@kaapanaApi.route('/api/curation_tool/format_metadata', methods=['POST'])
@csrf.exempt
def format_metadata():
    from dicom_parser.utils.vr_to_data_element import get_data_element_class
    from pydicom import Dataset

    # note! go into airflow pod and run: pip install dicom_parser!

    data = request.get_json(force=True)
    dataset = Dataset.from_json(data)
    parsed_and_filtered_data = [
        get_data_element_class(dataElement)(dataElement)
        for _, dataElement in dataset.items()
        if dataElement.VR != 'SQ' and dataElement.VR != 'OW' and dataElement.keyword != ''
    ]

    res = []
    for d_ in parsed_and_filtered_data:
        value = d_.value
        if d_.VALUE_REPRESENTATION.name == 'PN':
            value = "".join([v + " " for v in d_.value.values() if v != ""])
        res.append(
            dict(
                name=d_.description,
                value=str(value)
            )
        )
    return jsonify(res), 200

@kaapanaApi.route('/api/curation_tool/unstructured', methods=['POST'])
@csrf.exempt
def get_query_elastic_unstructured():
    query = request.get_json(force=True)
    if not query:
        query = {"query_string": {"query": "*"}}

    try:
        res = HelperOpensearch.os_client.search(body={
            "query": query,
            "size": 10000,
            "_source": {
                "includes": [
                    "00100020 PatientID_keyword",
                    "00100040 PatientSex_keyword",
                    "00101010 PatientAge_integer",
                    "0020000D StudyInstanceUID_keyword",
                    "0020000E SeriesInstanceUID_keyword",
                    "00080018 SOPInstanceUID_keyword",
                    "00081030 StudyDescription_keyword",
                    "0008103E SeriesDescription_keyword",
                    "00100010 PatientName_keyword_alphabetic",
                    "00080021 SeriesDate_date",
                    "00080020 StudyDate_date",
                    "dataset_tags_keyword"
                ]
            }
        }, index='meta-index')

    except Exception as e:
        print("ERROR in elasticsearch search!")
        return jsonify({'Error message': e}), 500

    return jsonify([d['_source'] for d in res['hits']['hits']]), 200

@kaapanaApi.route(
    '/api/curation_tool/seriesInstanceUID/<string:seriesInstanceUID>')
@csrf.exempt
def get_data_for_series_instance_UID(seriesInstanceUID):
    try:
        res = HelperOpensearch.os_client.search(body={
            "query": {
                "ids": {
                    "values": [seriesInstanceUID]
                }
            }
        })
    except Exception as e:
        print("ERROR in elasticsearch search!")
        return jsonify({'Error message': e}), 500

    return jsonify(res['hits']['hits'][0]['_source']), 200


@kaapanaApi.route('/api/curation_tool/query_values', methods=['POST'])
@csrf.exempt
def get_query_values():
    import re

    query = request.get_json(force=True)
    if not query:
        query = {"query_string": {"query": "*"}}

    def camel_case_to_space(s):
        return " ".join(re.sub(
            '([A-Z][a-z]+)', r' \1',
            re.sub(
                '([A-Z]+)', r' \1',
                " ".join(" ".join(s.split(" ")[-1::]).split("_")[:-1])
            )
        ).split())

    def type_suffix(v):
        if 'type' in v:
            type_ = v['type']
            return '' if type_ != 'text' and type_ != 'keyword' else '.keyword'
        else:
            return ''

    try:
        res = HelperOpensearch.os_client.indices.get_mapping("meta-index")['meta-index']['mappings']['properties']
        name_field_map = {
            camel_case_to_space(k): k + type_suffix(v)
            for k, v in res.items()
        }
        name_field_map = {
            k: v for k,v in name_field_map.items()
            if len(re.findall('\d', k)) == 0 and k != '' and v != ''
        }

        res = HelperOpensearch.os_client.search(body={
            "size": 0,
            "query": query,
            "aggs": {
                name: {
                    "terms": {
                        "field": field,
                        "size": 10000
                    }
                }
                for name, field in name_field_map.items()
            }
        })

    except Exception as e:
        print("ERROR in elasticsearch search!")
        return jsonify({'Error message': e}), 500

    result = {
        k: {
            'items': (
                [
                    dict(
                        text=f"{(i['key_as_string'] if 'key_as_string' in i else i['key'])}  ({i['doc_count']})",
                        value=(i['key_as_string'] if 'key_as_string' in i else i['key']),
                        count=i['doc_count']
                     )
                    for i in item['buckets']
                ]
            ),
            'key': name_field_map[k]
        }
        for k, item in res['aggregations'].items()
        if len(item['buckets']) > 0
    }

    return jsonify(result), 200