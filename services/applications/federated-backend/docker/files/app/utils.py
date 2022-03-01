import json
import os
import requests
from datetime import timezone, timedelta
import datetime
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from app import crud
from app import schemas

from elasticsearch import Elasticsearch
from minio import Minio


HOSTNAME = os.environ['HOSTNAME']
NODE_ID = os.environ['NODE_ID']


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
    def add_minio_urls(job_federated_data, local_federated_data, node_id): 
        federated_dir = local_federated_data['federated_dir']
        federated_bucket = local_federated_data['federated_bucket']
        if 'fl_round' in job_federated_data:
            fl_round = str(job_federated_data['fl_round'])
        else:
            fl_round = ''

        if not HelperMinio.minioClient.bucket_exists(federated_bucket):
            HelperMinio.minioClient.make_bucket(federated_bucket)

        minio_urls = {}
        for federated_operator in job_federated_data['federated_operators']:
            minio_urls[federated_operator] = {  
                'get': HelperMinio.get_custom_presigend_url('GET', federated_bucket, os.path.join(federated_dir, fl_round, node_id, f'{federated_operator}.tar.gz')),
                'put': HelperMinio.get_custom_presigend_url('PUT', federated_bucket,  os.path.join(federated_dir, fl_round, node_id, f'{federated_operator}.tar.gz'))
            }
        return minio_urls

    # @staticmethod
    # def apply_action_to_file(minioClient, action, bucket_name, object_name, file_path, file_white_tuples=None):
    #     print(file_path)
    #     if file_white_tuples is not None and not file_path.lower().endswith(file_white_tuples):
    #         print(f'Not applying action to object {object_name}, since this action is only allowed for files that end with {file_white_tuples}!')
    #         return
    #     if action == 'get': 
    #         print(f"Getting file: {object_name} from {bucket_name} to {file_path}")
    #         try:
    #             minioClient.stat_object(bucket_name, object_name)
    #             os.makedirs(os.path.dirname(file_path), exist_ok=True)
    #             minioClient.fget_object(bucket_name, object_name, file_path)
    #         except S3Error as err:
    #             print(f"Skipping object {object_name} since it doe not exists in Minio")
    #         except InvalidResponseError as err:
    #             print(err)
    #     elif action == 'remove':
    #         print(f"Removing file: {object_name} from {bucket_name}")
    #         try:
    #             minioClient.remove_object(bucket_name, object_name)
    #         except InvalidResponseError as err:
    #             print(err)
    #             raise
    #     elif action == 'put':
    #         print(f'Creating bucket {bucket_name} if it does not already exist.')
    #         HelperMinio.make_bucket(minioClient, bucket_name)
    #         print(f"Putting file: {file_path} to {bucket_name} to {object_name}") 
    #         try:
    #             minioClient.fput_object(bucket_name, object_name, file_path)
    #         except InvalidResponseError as err:
    #             print(err)
    #             raise
    #     else:
    #         raise NameError('You need to define an action: get, remove or put!')



# def get_presigend_url(minioClient, method, bucket_name, object_name, expires=timedelta(days=7)):
#     if method not in ['GET', 'PUT']:
#         raise NameError('Method must be either GET or PUT')
#     presigend_url = minioClient.get_presigned_url(method, bucket_name, object_name, expires=expires)
#     return {'method': method.lower(), 'path': presigend_url.replace(f'{minioClient._base_url._url.scheme}://{minioClient._base_url._url.netloc}', '')}

# def get_minio_client(access_key, secret_key, minio_host='minio-service.store.svc', minio_port='9000'):
#     minioClient = Minio(minio_host+":"+minio_port,
#                         access_key=access_key,
#                         secret_key=secret_key,
#                         secure=False)
#     return minioClient

def get_utc_timestamp():
    dt = datetime.datetime.now(timezone.utc)
    utc_time = dt.replace(tzinfo=timezone.utc)
    return utc_time

def get_dag_list(only_dag_names=True, filter_allowed_dags=[]):
    r = requests.get('http://airflow-service.flow.svc:8080/flow/kaapana/api/getdags')
    raise_kaapana_connection_error(r)
    dags = r.json()
    if only_dag_names is True:
        return sorted(list(dags.keys()))
    else:
        if filter_allowed_dags:
            return {dag: dags[dag] for dag in filter_allowed_dags}
        else:
            return dags

def get_dataset_list(queryDict=None, unique_sets=False, elastic_index='meta-index'):
    _elastichost = "elastic-meta-service.meta.svc:9200"
    es = Elasticsearch(hosts=_elastichost)
    if queryDict is None:
        queryDict = {
            "query": {
                "match_all": {} 
            },
            "_source": ['00120020 ClinicalTrialProtocolID_keyword']
        }

    try:
        res = es.search(index=[elastic_index], body=queryDict, size=10000, from_=0)
    except Exception as e:
        print("ERROR in elasticsearch search!")
        print(e)
    if 'hits' in res and 'hits' in res['hits']:
        datasets = []
        for hit in res['hits']['hits']:
            dataset = hit['_source']['00120020 ClinicalTrialProtocolID_keyword']
            if isinstance(dataset, str):
                dataset = [dataset]
            datasets.append(dataset)
        if unique_sets is True:
            return sorted(list(set([d for item in datasets for d in item])))
        else:
            return datasets
    else:
        raise ValueError('Invalid elasticsearch query!')

def execute_workflow(db_client_kaapana, conf_data, dry_run, dag_id='meta-trigger'):
    if db_client_kaapana.node_id != NODE_ID and db_client_kaapana.host != HOSTNAME:
        print('Exeuting remote job')
        if conf_data['conf']['dag'] not in json.loads(db_client_kaapana.allowed_dags):
            raise HTTPException(status_code=403, detail=f"Dag {conf_data['conf']['dag']} is not allowed to be triggered from remote!")
        queried_data = get_dataset_list({'query': conf_data['conf']['query']})
        if not all([bool(set(d) & set(json.loads(db_client_kaapana.allowed_datasets))) for d in queried_data]):
            raise HTTPException(status_code=403, detail = f"Your query outputed data with the tags: " \
                f"{''.join(sorted(list(set([d for datasets in queried_data for d in datasets]))))}, " \
                f"but only the following tags are allowed to be used from remote: {','.join(json.loads(db_client_kaapana.allowed_datasets))} !")
        if dry_run is True:
            return 'dry_run'
    resp = requests.post(f'http://airflow-service.flow.svc:8080/flow/kaapana/api/trigger/{dag_id}',  json=conf_data)
    raise_kaapana_connection_error(resp)
    return resp

def execute_job(db_job):
    print('Executing', db_job.conf_data, db_job.dry_run)
    conf_data = json.loads(db_job.conf_data)
    job_data = json.loads(db_job.job_data)
    conf_data['conf'].update(job_data)
    conf_data['conf']['client_job_id'] = db_job.id
    resp = execute_workflow(db_job.kaapana_instance, conf_data, db_job.dry_run, db_job.dag_id)
    if resp == 'dry_run':
        return Response(f"The configuration for the allowed dags and datasets is okay!", 200)
    else:
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
        print(f'Deleting remote job {db_job.external_job_id}, {db_job.addressed_kaapana_node_id}')
        db_remote_kaapana_instance = crud.get_kaapana_instance(db, node_id=db_job.addressed_kaapana_node_id, remote=True)
        remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/federated-backend/remote'
        r = requests.delete(f'{remote_backend_url}/job', verify=db_remote_kaapana_instance.ssl_check, params={
            "job_id": db_job.external_job_id,
        }, headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
        raise_kaapana_connection_error(r)
        print(r.json())

def update_external_job(db: Session, db_job):
    if db_job.external_job_id is not None:
        print(f'Updating remote job {db_job.external_job_id}, {db_job.addressed_kaapana_node_id}')
        db_remote_kaapana_instance = crud.get_kaapana_instance(db, node_id=db_job.addressed_kaapana_node_id, remote=True)
        remote_backend_url = f'{db_remote_kaapana_instance.protocol}://{db_remote_kaapana_instance.host}:{db_remote_kaapana_instance.port}/federated-backend/remote'
        r = requests.put(f'{remote_backend_url}/job', verify=db_remote_kaapana_instance.ssl_check, json={
            "job_id": db_job.external_job_id,
            "run_id": db_job.run_id,
            "status": db_job.status,
            "description": db_job.description
        }, headers={'FederatedAuthorization': f'{db_remote_kaapana_instance.token}'})
        raise_kaapana_connection_error(r)
        print(r.json())