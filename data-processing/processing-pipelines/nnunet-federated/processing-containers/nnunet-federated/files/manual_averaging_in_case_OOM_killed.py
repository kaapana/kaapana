import os
import sys
from pathlib import Path
import uuid
import torch
import json
import pickle
import shutil
import collections
from argparse import Namespace
import os, psutil

sys.path.insert(0, '../')
sys.path.insert(0, '/kaapana/app')
from kaapana_federated.KaapanaFederatedTraining import KaapanaFederatedTrainingBase, timeit

############################################################################################################
# Needs adaptations!
federated_round = 451
current_dir = '/kaapana/app/nnunet-training/nnunet-federated-220627045607689042'
use_minio_mount = '/kaapana/app'
# instance_names = ['A', 'B', 'C', 'D', 'E']
instance_names = ['G', 'J', 'K', 'L', 'M']
############################################################################################################

self = Namespace(**{
    'fl_working_dir': current_dir,
    #'use_minio_mount': '/minio'
    'use_minio_mount': use_minio_mount # Adapted to jupyter notebook!
})
current_federated_round_dir = Path(os.path.join(self.fl_working_dir, str(federated_round)))
print(psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2)
# Not 100% sure if it is necessary to put those into functions, I did this to be sure to not allocated unnecssary memory...
def _sum_state_dicts(fname, idx):
    checkpoint = torch.load(fname, map_location=torch.device('cpu'))
    if idx==0:
        sum_state_dict = checkpoint['state_dict']
    else:
        sum_state_dict = torch.load('tmp_state_dict.pt')
        for key, value in checkpoint['state_dict'].items():
            sum_state_dict[key] =  sum_state_dict[key] + checkpoint['state_dict'][key]
    torch.save(sum_state_dict, 'tmp_state_dict.pt')

def _save_state_dict(fname, averaged_state_dict):
    checkpoint = torch.load(fname, map_location=torch.device('cpu'))
    checkpoint['state_dict'] = averaged_state_dict
    torch.save(checkpoint, fname)

print('Loading averaged checkpoints')
for idx, fname in enumerate(current_federated_round_dir.rglob('model_final_checkpoint.model')):
    print(fname)
    _sum_state_dicts(fname, idx)
    print(psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2)

sum_state_dict = torch.load('tmp_state_dict.pt')
os.remove("tmp_state_dict.pt")

averaged_state_dict = collections.OrderedDict()
for key, value in sum_state_dict.items():
    averaged_state_dict[key] = sum_state_dict[key] / (idx+1.)

print('Saving averaged checkpoints')
for idx, fname in enumerate(current_federated_round_dir.rglob('model_final_checkpoint.model')):
    print(fname)
    _save_state_dict(fname, averaged_state_dict)
    print(psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2)


for instance_name in instance_names:
    file_path = f'{current_dir}/{str(federated_round)}/{instance_name}/nnunet-training.tar'
    if os.path.exists(file_path):
        os.remove(file_path)
    next_object_name = f'{current_dir}/{str(federated_round+1)}/{instance_name}/nnunet-training.tar'
    file_dir = file_path.replace('.tar', '')
    KaapanaFederatedTrainingBase.apply_tar_action(file_path, file_dir)
    print(f'Uploading {file_path } to {next_object_name}')

    dst = os.path.join(self.use_minio_mount, 'nnunet-training', next_object_name)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(file_path, dst)