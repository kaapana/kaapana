import os
import glob
import shutil
import re
import requests
import warnings

tmp_prefix = '/kaapana/tmp/'
target_prefix = os.getenv('TARGET_PREFIX', '/kaapana/mounted/workflows/')

if not target_prefix.startswith(f"/kaapana/mounted/"):
    print(f"Unknown prefix {target_prefix=} -> issue")
    exit(1)

def listdir_nohidden(path):
    if target_prefix.startswith(f"/kaapana/mounted/workflows"):
        for f in os.listdir(path):
            if not f.endswith('.pyc') and not f.startswith('.') and not (f.startswith('__') and f.endswith('__')):
                yield f
    else:
        for f in os.listdir(path):
            if f.endswith('.tgz'):
                yield f

def get_images(target_dir):
    print("Searching for images...")
    default_registry_identifier =  "{default_registry}"
    default_version_identifier =  "{kaapana_build_version}"
    image_dict = {}
    file_paths = glob.glob(f'{target_dir}/**/*.py', recursive=True)
    print("Found %i files..." % len(file_paths))
    for file_path in file_paths:
        if os.path.isfile(file_path):
            print(f'Checking file: {file_path}')
            content = open(file_path).read()
            matches = re.findall(REGEX, content)
            if matches:
                for match in matches:
                    docker_registry_url = match[1] if default_registry_identifier not in match[1] else match[1].replace(default_registry_identifier,KAAPANA_DEFAULT_REGISTRY)
                    docker_image = match[3]
                    docker_version = match[4] if default_version_identifier not in match[4] else match[4].replace(default_version_identifier,KAAPANA_BUILD_VERSION)
                    print(f"{docker_registry_url=}")
                    print(f"{docker_image=}")
                    print(f"{docker_version=}")
                    
                    image_dict.update({f'{docker_registry_url}/{docker_image}:{docker_version}': {
                        'docker_registry_url': docker_registry_url,
                        'docker_image': docker_image,
                        'docker_version': docker_version
                    }})
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

    if rel_dest_path == "" or rel_dest_path == ".":
        print(f"Skipping root {rel_dest_path=}")
        continue

    if not rel_dest_path.startswith(f"plugins") \
        and not rel_dest_path.startswith("dags") \
            and not rel_dest_path.startswith("mounted_scripts") \
                and not rel_dest_path.startswith("extensions"):
        print(f"Unknown relative directory {rel_dest_path=} -> issue")
        exit(1)
        
    dest_path = os.path.join(target_prefix, rel_dest_path)
    
    print(f"Copy file: {file_path=} to {dest_path=}")

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
print(f'✓ Successfully applied action {action} to all the files')
print('################################################################################')

if not target_prefix.startswith(f"/kaapana/mounted/workflows"):
    print(f"Calling it a day since I am not any workflow-related file")
    exit()

ADMIN_NAMESPACE = os.getenv('ADMIN_NAMESPACE', None)
print(f'{ADMIN_NAMESPACE=}')
assert ADMIN_NAMESPACE
SERVICES_NAMESPACE = os.getenv('SERVICES_NAMESPACE', None)
print(f'{SERVICES_NAMESPACE=}')
assert SERVICES_NAMESPACE
KAAPANA_BUILD_VERSION = os.getenv('KAAPANA_BUILD_VERSION', None)
print(f'{KAAPANA_BUILD_VERSION=}')
assert KAAPANA_BUILD_VERSION
KAAPANA_DEFAULT_REGISTRY = os.getenv('KAAPANA_DEFAULT_REGISTRY', None)
print(f'{KAAPANA_DEFAULT_REGISTRY=}')
assert KAAPANA_DEFAULT_REGISTRY

REGEX = r'image=(\"|\'|f\"|f\')([\w\-\\{\}.]+)(\/[\w\-\.]+|)\/([\w\-\.]+):([\w\-\\{\}\.]+)(\"|\'|f\"|f\')'
HELM_API=f"http://kube-helm-service.{ADMIN_NAMESPACE}.svc:5000"
AIRFLOW_API = f"http://airflow-webserver-service.{SERVICES_NAMESPACE}.svc:8080/flow/kaapana/api/trigger/service-daily-cleanup-jobs"
     
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
    r = requests.post(AIRFLOW_API, json={})
    print(r.status_code)
    print(r.text)

if action == 'prefetch':
    print('Running forever :)')
    while True:
        pass
