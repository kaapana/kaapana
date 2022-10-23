import json
import os
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from datetime import timezone, timedelta
import datetime
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from . import schemas
from app.config import settings

from opensearchpy import OpenSearch
from minio import Minio

class HelperMinio():

    _minio_host='minio-service.store.svc'
    _minio_port='9000'
    minioClient = Minio(_minio_host+":"+_minio_port,
                        access_key=settings.minio_username,
                        secret_key=settings.minio_password,
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
                        'opensearch-service.meta,opensearch-service.meta.svc'\
                            'kaapana-backend-service.base,kaapana-backend-service.base.svc,' \
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
    dags = {dag: dag_data for dag, dag_data in dags.items() if ('ui_federated' in dag_data and dag_data['ui_federated'] is True) or ('ui_visible' in dag_data and dag_data['ui_visible'] is True)}
    if only_dag_names is True:
        return sorted(list(dags.keys()))
    else:
        if filter_allowed_dags is None:
            return dags
        elif filter_allowed_dags:
            return {dag: dags[dag] for dag in filter_allowed_dags if dag in dags}
        else:
            return {}

def get_dataset_list(unique_sets=False, opensearch_index='meta-index'):
    _opensearchhost = "opensearch-service.meta.svc:9200"
    os_client = OpenSearch(hosts=_opensearchhost)

    queryDict = {
        "query": {
            "match_all": {} 
                "match_all": {} 
            "match_all": {} 
                "match_all": {} 
            "match_all": {} 
        },
        "_source": ['dataset_tags_keyword']
    }

    try:
        res = os_client.search(index=[opensearch_index], body=queryDict, size=10000, from_=0)
    except Exception as e:
        print("ERROR in OpenSearch search!")
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
        raise ValueError('Invalid OpenSearch query!')
    # try:
    #     with requests.Session() as s:
    #         resp = requests_retry_session(session=s).get('http://os-dashboards-service.meta.svc:5601/meta/api/saved_objects/_find', params={"type": "query"})
    #         print(resp.text)
    #         raise_kaapana_connection_error(resp)
    #         return [c["id"] for c in resp.json()["saved_objects"]]
    # except:
    #     raise ValueError('Invalid OpenSearch query!')

def check_dag_id_and_dataset(db_client_kaapana, conf_data, dag_id, addressed_kaapana_instance_name):
    if addressed_kaapana_instance_name is not None and db_client_kaapana.instance_name != addressed_kaapana_instance_name:
        if dag_id not in json.loads(db_client_kaapana.allowed_dags):
            return f"Dag {dag_id} is not allowed to be triggered from remote!"
        if "opensearch_form" in conf_data:
            pass
            # ToDo adapt!
            # queried_data = get_dataset_list(conf_data["opensearch_form"])
            # if not queried_data or (not all([bool(set(d) & set(json.loads(db_client_kaapana.allowed_datasets))) for d in queried_data])):
            #     return f"Queried series with tags " \
            #         f"{', '.join(sorted(list(set([d for item in queried_data for d in item]))))} are not all part of allowed datasets:" \
            #         f"{', '.join(json.loads(db_client_kaapana.allowed_datasets))}!"
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
