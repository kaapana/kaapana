import json
import os
import requests
from fastapi import APIRouter, Depends, Request, Response, HTTPException

from elasticsearch import Elasticsearch


HOSTNAME = os.environ['HOSTNAME']
NODE_ID = os.environ['NODE_ID']


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
        res = es.search(index=[elastic_index],
                        body=queryDict, size=10000, from_=0)
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


def raise_kaapana_connection_error(r):
    if r.history:
        raise HTTPException(
            'You were redirect to the auth page. Your token is not valid!')
    try:
        r.raise_for_status()
    except:
        raise HTTPException(
            f'Something was not okay with your request code {r}: {r.text}!')
