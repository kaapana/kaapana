import os
import glob
import shutil
import re
import requests

tmp_prefix = '/tmp/'
workflow_prefix = '/workflows/'
HELM_API='http://kube-helm-service.kube-system.svc:5000/kube-helm-api'

def get_images(target_dir):
    print("Searching for images...")

    image_list = []
    file_paths = glob.glob(f'{target_dir}/**/*.py', recursive=True)
    print("Found %i files..." % len(file_paths))
    for file_path in file_paths:
        print(file_path)
        if os.path.isfile(file_path):
            print(f'Checking file: {file_path}')
            content = open(file_path).read()
            findings = [m.start()
                        for m in re.finditer("image\s*=\s*('|\")", content)]

            for finding in findings:
                id_index = finding
                image_id = content[id_index:].split("\n")[0].split("=")[1].replace(
                    "\"", "").replace("'", "").replace(" ", "").replace(",", "")
                print("Found: % s" % image_id)
                image_list.append(image_id)
        else:
            print(f'Skipping directory: {file_path}')
    image_list=list(set(image_list))
    print("Found %i images to download..." % len(image_list))
    return image_list

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
            #shutil.chown(dest_path)
            #os.rmdir()
        if action == 'remove':
            if os.path.isdir(dest_path) and not os.listdir(dest_path):
                os.rmdir(dest_path)
    else:
        if os.path.isfile(dest_path) and action == 'copy':
            raise NameError('File exists already!')
        else:
            if action == 'copy':
                shutil.copyfile(file_path, dest_path)
                #shutil.chown(file_path)
            elif action == 'remove':
                if os.path.isfile(dest_path):
                    os.remove(dest_path)
            else:
                raise NameError('Action must be either copy or remove')


print('################################################################################')
print(f'Successfully applied action {action} to all the files')
print('################################################################################')


if action == 'copy':
    url = f'{HELM_API}/pull-docker-image'
    regex = r"([\w\-\.]+)(\/[\w\-\.]+|)\/([\w\-\.]+):([\w\-\.]+)"

    for image in get_images(tmp_prefix):
        match = re.match(regex, image)
        if match is not None:
            payload = {
                'docker_registry_url': match[1],
                'docker_registry_project': match[2],
                'docker_image': match[3],
                'docker_version': match[4]
            }
        print(payload)
        r = requests.post(url, json=payload)
        print(r.status_code)
        print(r.text)

print('################################################################################')
print(f'Successfully triggered the deployment to download the images of the dag')
print('################################################################################')