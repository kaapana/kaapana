import json
import os
import requests
from fastapi import APIRouter, Depends, Request, Response, HTTPException

from elasticsearch import Elasticsearch


def get_dag_list():
    r = requests.get('http://airflow-service.flow.svc:8080/flow/kaapana/api/getdags')
    return list(r.json().keys())

def get_dataset_list(queryDict=None, elastic_index='meta-index'):
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
        return datasets
    else:
        raise ValueError('Invalid elasticsearch query!')

def execute_workflow(db_client_kaapana, conf_data, dry_run):
    if conf_data['conf']['dag'] not in json.loads(db_client_kaapana.allowed_dags):
        raise HTTPException(status_code=403, detail=f"Dag {conf_data['conf']['dag']} is not allowed to be triggered from remote!")
    queried_data = get_dataset_list({'query': conf_data['conf']['query']})
    if not all([bool(set(d) & set(json.loads(db_client_kaapana.allowed_datasets))) for d in queried_data]):
        raise HTTPException(status_code=403, detail = f"Your query outputed data with the tags: " \
            f"{''.join(sorted(list(set([d for datasets in queried_data for d in datasets]))))}, " \
            f"but only the following tags are allowed to be used from remote: {','.join(json.loads(db_client_kaapana.allowed_datasets))} !")
    if dry_run is True:
        return 'dry_run'
    resp = requests.post('http://airflow-service.flow.svc:8080/flow/kaapana/api/trigger/meta-trigger',  json=conf_data)
    return resp

def raise_kaapana_connection_error(r):
    if r.history:
        raise HTTPException('You were redirect to the auth page. Your token is not valid!')
    try:
        r.raise_for_status()
    except:
        raise HTTPException(f'Something was not okay with your request code {r}: {r.text}!')
