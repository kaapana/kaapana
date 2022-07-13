import json
import os
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from datetime import timezone, timedelta
import datetime
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from app import crud
from app import schemas


from elasticsearch import Elasticsearch
from minio import Minio


HOSTNAME = os.environ['HOSTNAME']
INSTANCE_NAME = os.environ['INSTANCE_NAME']


class HelperMinio():

    _minio_host='minio-service.store.svc'
    _minio_port='9000'
    minioClient = Minio(_minio_host+":"+_minio_port,
                        access_key=os.environ.get('MINIOUSER'),
                        secret_key=os.environ.get('MINIOPASSWORD'),
                        secure=False)

    @staticmethod
    def get_custom_presigend_url(method, bucket_name, object_name, expires=timedelta(days=7)):
        if method not in ['GET', 'PUT']:
            raise NameError('Method must be either GET or PUT')
        presigend_url = HelperMinio.minioClient.get_presigned_url(method, bucket_name, object_name, expires=expires)
        return {'method': method.lower(), 'path': presigend_url.replace(f'{HelperMinio.minioClient._base_url._url.scheme}://{HelperMinio.minioClient._base_url._url.netloc}', '')}

    @staticmethod
    def add_minio_urls(federated, instance_name): 
        federated_dir = federated['federated_dir']
        federated_bucket = federated['federated_bucket']
        if 'federated_round' in federated:
            federated_round = str(federated['federated_round'])
        else:
            federated_round = ''

        if not HelperMinio.minioClient.bucket_exists(federated_bucket):
            HelperMinio.minioClient.make_bucket(federated_bucket)

        minio_urls = {}
        for federated_operator in federated['federated_operators']:
            minio_urls[federated_operator] = {  
                'get': HelperMinio.get_custom_presigend_url('GET', federated_bucket, os.path.join(federated_dir, federated_round, instance_name, f'{federated_operator}.tar')),
                'put': HelperMinio.get_custom_presigend_url('PUT', federated_bucket,  os.path.join(federated_dir, federated_round, instance_name, f'{federated_operator}.tar'))
            }
        return minio_urls


#https://www.peterbe.com/plog/best-practice-with-retries-with-requests
#https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/
def requests_retry_session(
    retries=16,
    backoff_factor=1,
    status_forcelist=[404, 429, 500, 502, 503, 504],
    session=None,
    use_proxies=False
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    if use_proxies is True:
        proxies = {
            'http': os.getenv('PROXY', None),
            'https': os.getenv('PROXY', None),
            'no_proxy': 'airflow-service.flow,airflow-service.flow.svc,' \
                'ctp-dicom-service.flow,ctp-dicom-service.flow.svc,'\
                    'dcm4chee-service.store,dcm4chee-service.store.svc,'\
                        'elastic-meta-service.meta,elastic-meta-service.meta.svc'\
                            'federated-backend-service.base,federated-backend-service.base.svc,' \
                                'minio-service.store,minio-service.store.svc'
        }
        session.proxies.update(proxies)

    return session 

def get_utc_timestamp():
    dt = datetime.datetime.now(timezone.utc)
    utc_time = dt.replace(tzinfo=timezone.utc)
    return utc_time

def get_dag_list(only_dag_names=True, filter_allowed_dags=None):
    with requests.Session() as s:
        r = requests_retry_session(session=s).get('http://airflow-service.flow.svc:8080/flow/kaapana/api/getdags')
    raise_kaapana_connection_error(r)
    dags = r.json()
    dags = {dag: dag_data for dag, dag_data in dags.items() if 'ui_forms' in dag_data}
    if only_dag_names is True:
        return sorted(list(dags.keys()))
    else:
        if filter_allowed_dags is None:
            return dags
        elif filter_allowed_dags:
            return {dag: dags[dag] for dag in filter_allowed_dags if dag in dags}
        else:
            return {}

def get_dataset_list(elasticsearch_data=None, unique_sets=False, elastic_index='meta-index'):
    _elastichost = "elastic-meta-service.meta.svc:9200"
    es = Elasticsearch(hosts=_elastichost)

    # copied from kaapana_api.py and HelperElatissearch.py should be part of Kapaana python library!
    if elasticsearch_data is None:
        queryDict = {
            "query": {
                "match_all": {} 
            },
            "_source": ['dataset_tags_keyword']
        }
    else:
        if "query" in elasticsearch_data:
            elastic_query = elasticsearch_data["query"]  
        elif "dataset" in elasticsearch_data or "input_modality" in elasticsearch_data:
            elastic_query = {
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

            if "dataset" in elasticsearch_data:
                elastic_query["bool"]["must"].append({
                    "match_phrase": {
                        "dataset_tags_keyword.keyword": {
                            "query": elasticsearch_data["dataset"]
                        }
                    }
                })
            if "input_modality" in elasticsearch_data:
                elastic_query["bool"]["must"].append({
                    "match_phrase": {
                        "00080060 Modality_keyword.keyword": {
                            "query": elasticsearch_data["input_modality"]
                        }
                    }
                })

        study_uid_tag = "0020000D StudyInstanceUID_keyword"
        series_uid_tag = "0020000E SeriesInstanceUID_keyword"
        SOPInstanceUID_tag = "00080018 SOPInstanceUID_keyword"
        modality_tag = "00080060 Modality_keyword"
        protocol_name_tag = "00181030 ProtocolName_keyword"
        queryDict = {}
        queryDict["query"] = elastic_query
        queryDict["_source"] = {"includes": [study_uid_tag, series_uid_tag,
                                             SOPInstanceUID_tag, modality_tag,
                                             protocol_name_tag, 'dataset_tags_keyword']}
                                             

    try:
        res = es.search(index=[elastic_index], body=queryDict, size=10000, from_=0)
    except Exception as e:
        print("ERROR in elasticsearch search!")
        print(e)
    if 'hits' in res and 'hits' in res['hits']:
        datasets = []
        for hit in res['hits']['hits']:
            dataset = hit['_source']['dataset_tags_keyword']
            if isinstance(dataset, str):
                dataset = [dataset]
            datasets.append(dataset)
        if unique_sets is True:
            return sorted(list(set([d for item in datasets for d in item])))
        else:
            return datasets
    else:
        raise ValueError('Invalid elasticsearch query!')

def check_dag_id_and_dataset(db_client_kaapana, conf_data, dag_id, addressed_kaapana_instance_name):
    if addressed_kaapana_instance_name is not None and db_client_kaapana.instance_name != addressed_kaapana_instance_name:
        if dag_id not in json.loads(db_client_kaapana.allowed_dags):
            return f"Dag {dag_id} is not allowed to be triggered from remote!"
        if "elasticsearch_form" in conf_data:
            queried_data = get_dataset_list(conf_data["elasticsearch_form"])
            if not queried_data or (not all([bool(set(d) & set(json.loads(db_client_kaapana.allowed_datasets))) for d in queried_data])):
                return f"Queried series with tags " \
                    f"{', '.join(sorted(list(set([d for item in queried_data for d in item]))))} are not all part of allowed datasets:" \
                    f"{', '.join(json.loads(db_client_kaapana.allowed_datasets))}!"
    return None

def execute_job(conf_data, dag_id):
    with requests.Session() as s:
        resp = requests_retry_session(session=s).post(f'http://airflow-service.flow.svc:8080/flow/kaapana/api/trigger/{dag_id}',  json={
            'conf': {
                **conf_data,
            }})
    raise_kaapana_connection_error(resp)
    return resp

def raise_kaapana_connection_error(r):
    if r.history:
        raise HTTPException('You were redirect to the auth page. Your token is not valid!')
    try:
        r.raise_for_status()
    except:
        raise HTTPException(f'Something was not okay with your request code {r}: {r.text}!')

def delete_external_job(db: Session, db_job):
    if db_job.external_job_id is not None:
        print(f'Deleting remote job {db_job.external_job_id}, {db_job.addressed_kaapana_instance_name}')
        same_instance = db_job.addressed_kaapana_instance_name == INSTANCE_NAME
        db_remote_kaapana_instance = crud.get_kaapana_instance(db, instance_name=db_job.addressed_kaapana_instance_name, remote=True)
        params = {
            "job_id": db_job.external_job_id,
        }
        if same_instance:
            crud.delete_job(db, **params)
        else:
            remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/federated-backend/remote'
            with requests.Session() as s:          
                r = requests_retry_session(session=s).delete(f'{remote_backend_url}/job', verify=db_remote_kaapana_instance.ssl_check, params=params, headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
            if r.status_code == 404:
                print(f'External job {db_job.external_job_id} does not exist')
            else:
                raise_kaapana_connection_error(r)
                print(r.json())

def update_external_job(db: Session, db_job):
    if db_job.external_job_id is not None:
        print(f'Updating remote job {db_job.external_job_id}, {db_job.addressed_kaapana_instance_name}')
        same_instance = db_job.addressed_kaapana_instance_name == INSTANCE_NAME
        db_remote_kaapana_instance = crud.get_kaapana_instance(db, instance_name=db_job.addressed_kaapana_instance_name, remote=True)
        payload = {
                "job_id": db_job.external_job_id,
                "run_id": db_job.run_id,
                "status": db_job.status,
                "description": db_job.description
            }
        if same_instance:
            crud.update_job(db, schemas.JobUpdate(**payload))
        else:
            remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/federated-backend/remote'
            with requests.Session() as s:                            
                r = requests_retry_session(session=s).put(f'{remote_backend_url}/job', verify=db_remote_kaapana_instance.ssl_check, json=payload, headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
            if r.status_code == 404:
                print(f'External job {db_job.external_job_id} does not exist')
            else:
                raise_kaapana_connection_error(r)
                print(r.json())


def get_remote_updates(db: Session, periodically=False):
    db_client_kaapana = crud.get_kaapana_instance(db, remote=False)
    if periodically is True and db_client_kaapana.automatic_update is False:
        return
    db_remote_kaapana_instances = crud.get_kaapana_instances(db, filter_kaapana_instances=schemas.FilterKaapanaInstances(**{'remote': True}))
    for db_remote_kaapana_instance in db_remote_kaapana_instances:
        same_instance = db_remote_kaapana_instance.instance_name == INSTANCE_NAME
        update_remote_instance_payload = {
            "instance_name":  db_client_kaapana.instance_name,
            "allowed_dags": json.loads(db_client_kaapana.allowed_dags),
            "allowed_datasets": json.loads(db_client_kaapana.allowed_datasets),
            "automatic_update": db_client_kaapana.automatic_update,
            "automatic_job_execution": db_client_kaapana.automatic_job_execution
            }

        job_params = {
            "instance_name": db_client_kaapana.instance_name,
            "status": "queued"
        }
        if same_instance is True:
            incoming_data = crud.sync_client_remote(db=db, remote_kaapana_instance=schemas.RemoteKaapanaInstanceUpdateExternal(**update_remote_instance_payload), **job_params)
        else:
            remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/federated-backend/remote'
            with requests.Session() as s:     
                r = requests_retry_session(session=s).put(f'{remote_backend_url}/sync-client-remote', params=job_params,  json=update_remote_instance_payload, verify=db_remote_kaapana_instance.ssl_check, 
            headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
            if r.status_code == 405:
                print(f'Warning!!! We could not reach the following backend {db_remote_kaapana_instance.host}')
                continue
            raise_kaapana_connection_error(r)
            incoming_data =  r.json()
        incoming_jobs = incoming_data['incoming_jobs']
        remote_kaapana_instance = schemas.RemoteKaapanaInstanceUpdateExternal(**incoming_data['update_remote_instance_payload'])

        crud.create_and_update_remote_kaapana_instance(db=db, remote_kaapana_instance=remote_kaapana_instance, action='external_update')

        for incoming_job in incoming_jobs:
            print('Creating', incoming_job["id"])
            incoming_job['kaapana_instance_id'] = db_client_kaapana.id
            incoming_job['addressed_kaapana_instance_name'] = db_remote_kaapana_instance.instance_name
            incoming_job['external_job_id'] = incoming_job["id"]
            incoming_job['status'] = "pending"
            job = schemas.JobCreate(**incoming_job)
            db_job = crud.create_job(db, job)

    return #schemas.RemoteKaapanaInstanceUpdateExternal(**udpate_instance_payload)
