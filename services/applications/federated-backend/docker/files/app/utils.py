import requests
from app import es

def get_dag_list():
    r = requests.get('http://airflow-service.flow.svc:8080/flow/kaapana/api/getdags')
    return list(r.json().keys())

def get_dataset_list(queryDict=None, elastic_index='meta-index'):
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
