import os
import glob
import shutil
import re
import requests
import warnings

tmp_prefix = '/tmp/'
workflow_prefix = '/workflows/'
HELM_API='http://kube-helm-service.kube-system.svc:5000/kube-helm-api'

regex = r'image=(\"|\'|f\"|f\')([\w\-\\{\}.]+)(\/[\w\-\.]+|)\/([\w\-\.]+):([\w\-\.]+)(\"|\'|f\"|f\')'

def listdir_nohidden(path):
    for f in os.listdir(path):
        if not f.endswith('.pyc') and not f.startswith('.') and not (f.startswith('__') and f.endswith('__')):
            yield f

def get_images(target_dir):
    print("Searching for images...")
    image_dict = {}
    file_paths = glob.glob(f'{target_dir}/**/*.py', recursive=True)
    print("Found %i files..." % len(file_paths))
    for file_path in file_paths:
        if os.path.isfile(file_path):
            print(f'Checking file: {file_path}')
            content = open(file_path).read()
            matches = re.findall(regex, content)
            if matches:
                for match in matches:
                    docker_registry_url = match[1] if '{' not in match[1] else ''
                    docker_registry_project = match[2]
                    docker_image = match[3]
                    docker_version = match[4]
                    image_dict.update({f'{docker_registry_url}{docker_registry_project}/{docker_image}:{docker_version}': {
                        'docker_registry_url': docker_registry_url,
                        'docker_registry_project': docker_registry_project,
                        'docker_image': docker_image,
                        'docker_version': docker_version
                    }})
                    print(f'{docker_registry_url}{docker_registry_project}/{docker_image}:{docker_version}')
        else:
            print(f'Skipping directory: {file_path}')
    print("Found %i images to download..." % len(image_dict))
    return image_dict

action = os.getenv('ACTION', 'copy')
print(f'Apply action {action} to files')
files_to_copy = glob.glob(f'{tmp_prefix}**', recursive=True)
if action == 'remove':
    files_to_copy = reversed(files_to_copy)

for file_path in files_to_copy:
    rel_dest_path = os.path.relpath(file_path, tmp_prefix)
    rel_dest_path = '' if rel_dest_path== '.' else rel_dest_path
    dest_path = os.path.join(workflow_prefix, rel_dest_path)
    print(file_path, dest_path)
    if os.path.isdir(file_path):
        if not os.path.isdir(dest_path) and action == 'copy':
            os.makedirs(dest_path)
        if action == 'remove':
            if os.path.isdir(dest_path) and not list(listdir_nohidden(dest_path)):
                shutil.rmtree(dest_path, ignore_errors=True)
    else:
        if action == 'copy':
            if os.path.isfile(dest_path) and action == 'copy':
                warnings.warn(f"Attention! You are overwriting the file {dest_path}!")
                #raise NameError('File exists already!')
            shutil.copyfile(file_path, dest_path)
        elif action == 'remove':
            if os.path.isfile(dest_path):
                os.remove(dest_path)
        else:
            pass


print('################################################################################')
print(f'Successfully applied action {action} to all the files')
print('################################################################################')


if action == 'copy' or action == 'prefetch':
    url = f'{HELM_API}/pull-docker-image'
    for name, payload in get_images(tmp_prefix).items():
        print(payload)
        r = requests.post(url, json=payload)
        print(r.status_code)
        print(r.text)

if action == 'remove':
    print('################################################################################')
    print(f'Updating dags in airflow database!')
    print('################################################################################')
    r = requests.post('http://airflow-service.flow.svc:8080/flow/kaapana/api/trigger/remove-deleted-dags-from-db', json={})
    print(r.status_code)
    print(r.text)

if action == 'prefetch':
    print('Running forever :)')
    while True:
        pass
