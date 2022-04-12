import re
import os
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from xml.etree import ElementTree
from datetime import datetime


from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


def generate_run_id(dag_id):
    run_id = datetime.now().strftime('%y%m%d%H%M%S%f')
    run_id = "{}-{}".format(dag_id, run_id)
    return run_id


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
        name = name[:max_length]
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

# Same as in federated-backend/docker/files/app/utils.py
#https://www.peterbe.com/plog/best-practice-with-retries-with-requests
#https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/
def requests_retry_session(
    retries=15, # Retries for 18.2 hours
    backoff_factor=2,
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