import re
import os
import shutil
import requests
import tarfile
import time
import urllib3
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from xml.etree import ElementTree
from datetime import datetime
from socket import timeout


from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


def generate_run_id(dag_id):
    run_id = datetime.now().strftime('%y%m%d%H%M%S%f')
    run_id = "{}-{}".format(dag_id, run_id)
    return run_id

def get_release_name(kwargs):
    run_id = kwargs['run_id']
    release_name = cure_invalid_name(run_id, r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*", max_length=42) # actually 53, but becuse of kaapana-int- 42
    return f'kaapanaint-{release_name}'


def generate_minio_credentials(x_auth_token):
    # Not sure if DurationSeconds has an influence, this WebIdentitytoken maybe defines the session period
    # Version is hard-coded, check https://github.com/minio/minio/blob/master/docs/sts/web-identity.md for more information!
    r = requests.post(f'http://minio-service.store.svc:9000?Action=AssumeRoleWithWebIdentity&DurationSeconds=3600&WebIdentityToken={x_auth_token}&Version=2011-06-15')
    r.raise_for_status()
    tree = ElementTree.fromstring(r.content)
    assume_role_with_web_identity_result = tree.find('{https://sts.amazonaws.com/doc/2011-06-15/}AssumeRoleWithWebIdentityResult')
    credentials = assume_role_with_web_identity_result.find('{https://sts.amazonaws.com/doc/2011-06-15/}Credentials')
    access_key = credentials.find('{https://sts.amazonaws.com/doc/2011-06-15/}AccessKeyId').text
    secret_key = credentials.find('{https://sts.amazonaws.com/doc/2011-06-15/}SecretAccessKey').text
    session_token = credentials.find('{https://sts.amazonaws.com/doc/2011-06-15/}SessionToken').text
    return access_key, secret_key, session_token


def cure_invalid_name(name, regex, max_length=None):
    def _regex_match(regex, name):
        if re.fullmatch(regex, name) is None:
            invalid_characters = re.sub(regex, '', name)
            for c in invalid_characters:
                name = name.replace(c, '')
            print(f'Your name does not fullfill the regex {regex}, we adapt it to {name} to work with Kubernetes')
        return name
    name = _regex_match(regex, name)
    if max_length is not None and len(name) > max_length:
        name = name[-max_length:]
        print(f'Your name is too long, only {max_length} character are allowed, we will cut it to {name} to work with Kubernetes')
    name = _regex_match(regex, name)
    return name


def get_operator_properties(*args, **kwargs):
    if 'context' in kwargs:
        run_id = kwargs['context']['run_id']
        dag_run = kwargs['context']['dag_run']
        downstream_tasks = kwargs['context']['task'].get_flat_relatives(upstream=False)

    elif type(args) == tuple and len(args) == 1 and "run_id" in args[0]:
        raise ValueError('Just to check if this case needs to be supported!', args, kwargs)
        run_id = args[0]['run_id']
    else:
        run_id = kwargs['run_id']
        dag_run = kwargs['dag_run']
        downstream_tasks = kwargs['task'].get_flat_relatives(upstream=False)
    
    dag_run_dir = os.path.join(WORKFLOW_DIR, run_id)
    
    return run_id, dag_run_dir, dag_run, downstream_tasks


# Same as in kaapana-backend/docker/files/app/utils.py
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
            'no_proxy': 'airflow-service.flow,airflow-service.flow.svc,ctp-dicom-service.flow,ctp-dicom-service.flow.svc,dcm4chee-service.store,dcm4chee-service.store.svc,opensearch-service.meta,opensearch-service.meta.svc,kaapana-backend-service.base,kaapana-backend-service.base.svc,minio-service.store,minio-service.store.svc'
        }
        session.proxies.update(proxies)

    return session 

def trying_request_action(func, *args, **kwargs):
    max_retries = 10
    try_count = 0
    while try_count < max_retries:
        print("Try: {}".format(try_count))
        try_count += 1
        try:
            return func(*args, **kwargs)
        except tarfile.ReadError as e:
            print("The files was not downloaded properly...")
            print(e)
            time.sleep(5)
            print(f"Trying again action on {func.__name__}")
        except urllib3.exceptions.ReadTimeoutError as e:
            print("Reaad timeout error")
            print(e)
            print(f"Trying again action on {func.__name__}")
        except requests.exceptions.ConnectionError as e:
            print("Connection Error")
            print(e)
            print(f"Trying again action on {func.__name__}")
        except requests.exceptions.ChunkedEncodingError as e:
            print("ChunkedEncodingError")
            print(e)
            print(f"Trying again action on {func.__name__}")
        except urllib3.exceptions.ProtocolError as e:
            print("ProtocolError")
            print(e)
            print(f"Trying again action on {func.__name__}")
        except urllib3.exceptions.MaxRetryError as e:
            print("MaxRetryError")
            print(e)
            print(f"Trying again action on {func.__name__}")        
        except ValueError as e: # because of raise_kaapana_connection_error
            print("ValueError")
            print(e)
            print(f"Trying again action on {func.__name__}")            
        except timeout:
            print("Timeout")
            print(f"Trying again action on {func.__name__}")

    if try_count >= max_retries:
        print("------------------------------------")
        print("Max retries reached!")
        print("------------------------------------")
        raise ValueError(f"We were not able to apply action on {func.__name__}")


def clean_previous_dag_run(conf, run_identifier):
    if conf is not None and 'federated_form' in conf and conf['federated_form'] is not None:
        federated = conf['federated_form']
        if run_identifier in federated and federated[run_identifier] is not None:
            dag_run_dir = os.path.join(WORKFLOW_DIR, conf['federated_form'][run_identifier])
            print(f'Removing batch files from {run_identifier}: {dag_run_dir}')
            if os.path.isdir(dag_run_dir):
                shutil.rmtree(dag_run_dir)


def parse_ui_dict(dag_dict):

    if "ui_forms" in dag_dict:
        if "ui_visible" in dag_dict and dag_dict["ui_visible"] is True and "data_form" not in dag_dict["ui_forms"]:
            dag_dict["ui_forms"].update({
                "data_form": {
                    "type": "object",
                    "properties": {
                        "cohort_name": "$default",
                        "cohort_limit": "$default"
                    }
                }
            })

        default_properties = {}
        for ui_form_key, ui_form in dag_dict["ui_forms"].items():
            if ui_form_key=='publication_form':
                pass
            elif ui_form_key=='workflow_form':
                default_properties = {
                    "single_execution": {
                        "type": "boolean",
                        "title": "Single execution",
                        "description": "Whether your report is execute in single mode or not",
                        "default": True,
                        "readOnly": False,
                        "required": True
                    }
                }
            elif ui_form_key=='data_form':
                default_properties = {
                    "cohort_name": {
                        "type": "string",
                        "title": "Cohort name",
                        "oneOf": [],
                        "required": True
                    },
                    "cohort_limit": {
                        "type": "integer",
                        "title": "Limit cohort-size",
                        "description": "Limit Cohort to this many cases.",
                        "required": True
                    }
                }
            elif ui_form_key == 'external_schema_federated_form':
                default_properties = {
                    "federated_bucket": {
                        "type": "string",
                        "title": "Federated bucket",
                        "description": "Bucket to which the files should be saved to",
                        "readOnly": True
                    },
                    "federated_dir": {
                        "type": "string",
                        "title": "Federated directory",
                        "description": "Directory to which the files should be saved to",
                        "readOnly": True
                    },
                    "federated_operators": {
                        "type": "array",
                        "title": "Operators for which the results should be saved",
                        "items": {
                            "type": "string"
                        },
                        "readOnly": True
                    },
                    "skip_operators": {
                        "type": "array",
                        "title": "Operators that should not be executed",
                        "items": {
                            "type": "string"
                        },
                        "readOnly": True
                    },
                    "federated_round": {
                        "type": "integer",
                        "title": "Federated round",
                        "readOnly": True
                    },
                    "federated_total_rounds": {
                        "type": "integer",
                        "title": "Federated total rounds"
                    }
                }
            if 'properties' in ui_form:
                for k, v in ui_form['properties'].items():
                    if v == "$default":
                        ui_form['properties'][k] = default_properties[k]
    return dag_dict