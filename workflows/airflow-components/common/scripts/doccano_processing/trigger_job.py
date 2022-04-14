import sys, os
import glob
import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Should be moved from kaapana library in the future!
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
        proxies = {'http': os.getenv('PROXY', None), 'https': os.getenv('PROXY', None)}
        print('Setting proxies', proxies)
        session.proxies.update(proxies)
    else:
        print('Not using proxies!')

    return session 

batch_input_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])

with open(os.path.join(batch_input_dir, 'doccanoadmin.json') ) as f:
    annotations = json.load(f)
for annotation in annotations:
    ae_titles = ",".join(annotation['label'])
    study_id = annotation['data'][9:] 
    conf_data = {
        "query": {
            "bool": {
                "must": [
                    {
                        "match_all": {}
                    },
                    {
                        "match_all": {}
                    },
                    {
                        "bool": {
                            "should": [
                                {
                                    "match_phrase": {
                                        "0020000D StudyInstanceUID_keyword.keyword": study_id
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    }
                ],
                "filter": [],
                "should": [],
                "must_not": []
            }
        },
        "index": "meta-index",
        "dag": "send-dicom",
        "cohort_limit": 100,
        "form_data": {
            "host": os.getenv('HOSTDOMAIN'),
            "port": 11112,
            "aetitle": ae_titles,
            "single_execution": True
        }
    }
    print(conf_data)
    with requests.Session() as s:
        resp = requests_retry_session(session=s).post(f'http://airflow-service.flow.svc:8080/flow/kaapana/api/trigger/meta-trigger',  json={
            'conf': {
                **conf_data,
            }})

    print(resp)
    print(resp.text)
    resp.raise_for_status()