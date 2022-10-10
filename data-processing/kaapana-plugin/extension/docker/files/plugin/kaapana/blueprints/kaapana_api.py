import warnings
from flask import g, Blueprint, request, jsonify, Response, url_for
from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound
from datetime import datetime
import requests
import airflow.api
from http import HTTPStatus
from airflow.exceptions import AirflowException
from airflow.models import DagRun, DagModel, DAG, DagBag
from airflow import settings
from airflow.utils import timezone
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.www.app import csrf
import glob
import json
import time
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.blueprints.kaapana_utils import generate_minio_credentials
from airflow.api.common.trigger_dag import trigger_dag as trigger
from kaapana.operators.HelperOpensearch import HelperOpensearch
from flask import current_app as app
from multiprocessing.pool import ThreadPool

_log = LoggingMixin().log
parallel_processes = 1
"""
Represents a blueprint kaapanaApi
"""
kaapanaApi = Blueprint('kaapana', __name__, url_prefix='/kaapana')
def async_dag_trigger(queue_entry):
    hit, dag_id, tmp_conf, username = queue_entry
    hit = hit["_source"]
    studyUID = hit[HelperOpensearch.study_uid_tag]
    seriesUID = hit[HelperOpensearch.series_uid_tag]
    SOPInstanceUID = hit[HelperOpensearch.SOPInstanceUID_tag]
    modality = hit[HelperOpensearch.modality_tag]

    print(f"# Triggering {dag_id} - series: {seriesUID}")

    conf = {
        "user_public_id": username,
        "inputs": [
            {
                "dcm-uid": {
                    "study-uid": studyUID,
                    "series-uid": seriesUID,
                    "modality": modality
                }
            }
        ],
        **tmp_conf
        # "conf": tmp_conf
    }

    dag_run_id = generate_run_id(dag_id)
    try:
        result = trigger(dag_id=dag_id, run_id=dag_run_id, conf=conf, replace_microseconds=False)
    except Exception as e:
        pass

    return seriesUID, result

        
@csrf.exempt
@kaapanaApi.route('/api/trigger/<string:dag_id>', methods=['POST'])
def trigger_dag(dag_id):
    headers = dict(request.headers)
    data = request.get_json(force=True)
    username = headers["X-Forwarded-Preferred-Username"] if "X-Forwarded-Preferred-Username" in headers else "unknown"
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

    # temporary workaround for workflow-trigger not using meta-trigger as dag_id anymore
    tmp_conf['opensearch_form'] = {
        "query": tmp_conf["query"],
        "index": tmp_conf["index"],
        "single_execution": tmp_conf["workflow_form"]["single_execution"],
        "cohort_limit": int(tmp_conf["cohort_limit"]) if "cohort_limit" in tmp_conf and tmp_conf["cohort_limit"] is not None else None
    }

    if dag_id == "meta-trigger":
        warnings.warn("meta-trigger as endpoint was depcrecated in version 0.1.3, please adjust your request accordingly")
        form_data = tmp_conf["form_data"] if "form_data" in tmp_conf else None
        if form_data is not None:
            warnings.warn("form_data was renamed to workflow_data, please adjust your request accordingly")
        print(json.dumps(form_data))
        single_execution = True if form_data is not None and "single_execution" in form_data and form_data["single_execution"] else False
        dag_id = tmp_conf["dag"]
        tmp_conf['opensearch_form'] = {
            "query": tmp_conf["query"],
            "index": tmp_conf["index"],
            "single_execution": single_execution,
            "cohort_limit": int(tmp_conf["cohort_limit"]) if "cohort_limit" in tmp_conf and tmp_conf["cohort_limit"] is not None else None
        }
    ################################################################################################

    if "opensearch_form" in tmp_conf:
        opensearch_data = tmp_conf["opensearch_form"]
        if "query" in opensearch_data:
            query = opensearch_data["query"]
        elif "dataset" in opensearch_data or "input_modality" in opensearch_data:
            query = {
                "bool": {
                    "must": [
                        {
                            "match_all": {}
                        },
                        {
                            "match_all": {}
                        }
                    ],
                    "filter": [],
                    "should": [],
                    "must_not": []
                }
            }

            if "dataset" in opensearch_data:
                query["bool"]["must"].append({
                    "match_phrase": {
                        "dataset_tags_keyword.keyword": {
                            "query": opensearch_data["dataset"]
                        }
                    }
                })
            if "input_modality" in opensearch_data:
                query["bool"]["must"].append({
                    "match_phrase": {
                        "00080060 Modality_keyword.keyword": {
                            "query": opensearch_data["input_modality"]
                        }
                    }
                })
        else:
            raise ValueError('query or dataset or input_modality needs to be defined!')

        index = opensearch_data["index"]
        cohort_limit = int(opensearch_data["cohort_limit"]) if ("cohort_limit" in opensearch_data and opensearch_data["cohort_limit"] is not None) else None
        single_execution = True if "single_execution" in opensearch_data and opensearch_data["single_execution"] else False

        print(f"query: {query}")
        print(f"index: {index}")
        print(f"dag_id: {dag_id}")
        print(f"single_execution: {single_execution}")

        if single_execution:
            hits = HelperOpensearch.get_query_cohort(query=query, index=index)
            if hits is None:
                message = ["Error in HelperOpensearch: {}!".format(dag_id)]
                response = jsonify(message=message)
                response.status_code = 500
                return response

            hits = hits[:cohort_limit] if cohort_limit is not None else hits

            queue = []
            for hit in hits:
                queue.append((hit, dag_id, tmp_conf,username))

            trigger_results = ThreadPool(parallel_processes).imap_unordered(async_dag_trigger, queue)
            for seriesUID, result in trigger_results:
                print(f"#  Done: {seriesUID}:{result}")

        else:
            conf = {
                "user_public_id": username,
                "inputs": [
                    {
                        "opensearch-query": {
                            "query": query,
                            "index": index
                        }
                    }
                ],
                **tmp_conf
                # "conf": tmp_conf
            }
            dag_run_id = generate_run_id(dag_id)
            trigger(dag_id=dag_id, run_id=dag_run_id, conf=conf, replace_microseconds=False)

        message = ["{} created!".format(dag_id)]
        response = jsonify(message=message)
        return response

    else:
        run_id = generate_run_id(dag_id)

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
        dags[dag_id] = dag_dict

    app.config['JSON_SORT_KEYS'] = False
    return jsonify(dags)


def check_dag_exists(session, dag_id):
    """
    if returns an error response, if it doesn't exist
    """
    dag_exists = session.query(DagModel).filter(
        DagModel.dag_id == dag_id).count()
    if not dag_exists:
        return Response('Dag {} does not exist'.format(dag_id), http.client.BAD_REQUEST)

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
