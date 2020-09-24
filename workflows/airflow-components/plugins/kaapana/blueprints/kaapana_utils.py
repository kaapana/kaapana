import re
import requests
from xml.etree import ElementTree
from datetime import datetime

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
    if re.fullmatch(regex, name) is None:
        invalid_characters = re.sub(regex, '', name)
        for c in invalid_characters:
            name = name.replace(c, '')
        print(f'Your name does not fullfill the regex {regex}, we adapt it to {name} to work with Kubernetes')

    if max_length is not None and len(name) > max_length:
        name = name[:max_length]
        print(f'Your name is too long, only {max_length} character are allowed, we will cut it to {name} to work with Kubernetes')
    return name