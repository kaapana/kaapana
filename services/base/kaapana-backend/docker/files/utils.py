import json
import os
import requests
from fastapi import APIRouter, Depends, Request, Response, HTTPException

from opensearchpy import OpenSearch

# def get_dataset_list(queryDict=None, elastic_index='meta-index'):
#     _elastichost = "elastic-meta-service.meta.svc:9200"
#     es = Elasticsearch(hosts=_elastichost)
#     if queryDict is None:
#         queryDict = {
#             "query": {
#                 "match_all": {} 
#             },
#             "_source": ['00120020 ClinicalTrialProtocolID_keyword']
#         }

#     try:
#         res = es.search(index=[elastic_index], body=queryDict, size=10000, from_=0)
#     except Exception as e:
#         print("ERROR in elasticsearch search!")
#         print(e)
#     if 'hits' in res and 'hits' in res['hits']:
#         datasets = []
#         for hit in res['hits']['hits']:
#             dataset = hit['_source']['00120020 ClinicalTrialProtocolID_keyword']
#             if isinstance(dataset, str):
#                 dataset = [dataset]
#             datasets.append(dataset)
#         return datasets
#     else:
#         raise ValueError('Invalid elasticsearch query!')

def get_dataset_list(opensearch_data=None, unique_sets=False, opensearch_index='meta-index'):
    _opensearchhost = "opensearch-service.meta.svc:9200"
    os_client = OpenSearch(hosts=_opensearchhost)

    # copied from kaapana_api.py and HelperOpenSearch.py should be part of Kapaana python library!
    if opensearch_data is None:
        queryDict = {
            "query": {
                "match_all": {} 
            },
            "_source": ['dataset_tags_keyword']
        }
    else:
        if "query" in opensearch_data:
            opensearch_query = opensearch_data["query"]  
        elif "dataset" in opensearch_data or "input_modality" in opensearch_data:
            opensearch_query = {
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
                opensearch_query["bool"]["must"].append({
                    "match_phrase": {
                        "dataset_tags_keyword.keyword": {
                            "query": opensearch_data["dataset"]
                        }
                    }
                })
            if "input_modality" in opensearch_data:
                opensearch_query["bool"]["must"].append({
                    "match_phrase": {
                        "00080060 Modality_keyword.keyword": {
                            "query": opensearch_data["input_modality"]
                        }
                    }
                })

        study_uid_tag = "0020000D StudyInstanceUID_keyword"
        series_uid_tag = "0020000E SeriesInstanceUID_keyword"
        SOPInstanceUID_tag = "00080018 SOPInstanceUID_keyword"
        modality_tag = "00080060 Modality_keyword"
        protocol_name_tag = "00181030 ProtocolName_keyword"
        queryDict = {}
        queryDict["query"] = opensearch_query
        queryDict["_source"] = {"includes": [study_uid_tag, series_uid_tag,
                                             SOPInstanceUID_tag, modality_tag,
                                             protocol_name_tag, 'dataset_tags_keyword']}
                                             

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


def raise_kaapana_connection_error(r):
    if r.history:
        raise HTTPException(
            'You were redirect to the auth page. Your token is not valid!')
    try:
        r.raise_for_status()
    except:
        raise HTTPException(
            f'Something was not okay with your request code {r}: {r.text}!')
