import os
import glob
import shutil
import re
import warnings

tmp_prefix = '/tmp/'
extensions_prefix = os.getenv('CHARTS_DIR', '/charts/extensions')

def listdir_nohidden(path):
    for f in os.listdir(path):
        if f.endswith('.tgz'):
            yield f

action = os.getenv('ACTION', 'copy')
print(f'Apply action {action} to files')
files_to_copy = glob.glob(f'{tmp_prefix}**', recursive=True)
if action == 'remove':
    files_to_copy = reversed(files_to_copy)

for file_path in files_to_copy:
    rel_dest_path = os.path.relpath(file_path, tmp_prefix)
    rel_dest_path = '' if rel_dest_path== '.' else rel_dest_path
    dest_path = os.path.join(extensions_prefix, rel_dest_path)
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