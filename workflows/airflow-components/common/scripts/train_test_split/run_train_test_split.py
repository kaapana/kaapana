import sys, os
import glob
import json
import requests
import random
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

def send_dicoms(series_id, ae_titles):
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
                                        "0020000E SeriesInstanceUID_keyword.keyword": series_id
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
        "cohort_limit": 1,
        "form_data": {
            "host": "ctp-dicom-service.flow.svc",
            "port": 11112,
            "aetitle": ae_titles,
            "single_execution": True
        }
    }
    with requests.Session() as s:
        resp = requests_retry_session(session=s).post(f'http://airflow-service.flow.svc:8080/flow/kaapana/api/trigger/meta-trigger',  json={
            'conf': {
                **conf_data,
            }})

    resp.raise_for_status()

train_aetitle = os.getenv('TRAIN_AETITLE')
test_aetitle = os.getenv('TEST_AETITLE')
random_seed = int(os.getenv('RANDOM_SEED', 1))
split = float(os.getenv('SPLIT', 0.8))

print(f'Using train_aetitle: {train_aetitle}, test_aetitle: {test_aetitle}, split: {split} and random_seed: {random_seed}')

batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])


if split > 1:
    train_split = int(split)
else:
    train_split = round(split * len(batch_folders))

if train_split > len(batch_folders):
    raise ValueError('Train split is bigger than the number of selected samples!')

random.seed(random_seed)
random.shuffle(batch_folders)

print(f'Sending train data')
for batch_element_dir in batch_folders[:train_split]:
    series_id = os.path.basename(batch_element_dir)
    send_dicoms(series_id, train_aetitle)

print(f'Sending test data')
for batch_element_dir in batch_folders[train_split:]:
    series_id = os.path.basename(batch_element_dir)
    send_dicoms(series_id, test_aetitle)
