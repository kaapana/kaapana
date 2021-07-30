import os
import json
import time
from datetime import datetime

import syft as sy
from syft.grid.clients.data_centric_fl_client import DataCentricFLClient

import torch
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

from utils.utilities import provide_dataset_transforms

hook = sy.TorchHook(torch)


class Arguments():
    def __init__(self):
        self.host = os.getenv('HOSTNAME')
        self.port = os.getenv('PORT', '5000')
        self.node_addr = 'http://{}:{}/'.format(self.host, self.port)

        self.exp_tag = os.getenv('EXP_TAG', '#no-tag-given')
        self.dataset = os.getenv('DATASET', 'mnist')
        self.lifespan = int(os.getenv('LIFESPAN', '15'))
        self.data_path = os.path.join(os.environ["WORKFLOW_DIR"], os.environ['OPERATOR_IN_DIR'])

        self.log_dir = os.path.join(os.environ["WORKFLOW_DIR"], 'logging')
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)


def main(args):

    # get dataset specific image transforms
    transform_dict = provide_dataset_transforms(dataset=args.dataset)

    # Image folder
    dataset = ImageFolder(
        root=os.path.join(args.data_path, 'train'),
        transform=transform_dict['train'])
    print("Class encoding: {}".format(dataset.class_to_idx))

    # dataloader
    n_samples = len(dataset)
    print(f'Total dataset size: {n_samples}')
    dataloader = DataLoader(
        dataset,
        batch_size=n_samples,
        shuffle=True,
        num_workers=0)
    
    # get images & targets
    print('Start Iterator - applying data transforms!')
    dataiter = iter(dataloader)
    images, targets = dataiter.next()
    print('Passed Iterator!')

    # wait until PySyft-Node is available
    node = None
    while not node:
        time.sleep(5)
        try:
            node = DataCentricFLClient(hook, args.node_addr)
        except:
            pass
    
    # send data to node
    print(f'Sending data to node {node} - adrress: {args.node_addr}')
    
    imgs_description = f"images used for experiment {args.exp_tag} (dataset: {args.dataset})"
    imgs_tag = images.tag('#X', '#dataset', f"#{args.dataset}", args.exp_tag).describe(imgs_description)
    pointer = imgs_tag.send(node)
    print(pointer)
    print(f'Images send to node - description: {imgs_description}')

    targets_description = f"targets used for experiment {args.exp_tag} (dataset: {args.dataset})"
    targets_tag = targets.tag('#Y', '#dataset', f"#{args.dataset}", args.exp_tag).describe(targets_description)
    _ =  targets_tag.send(node)
    print(f'Targets send  to node - description: {targets_description}')

    # save timestamp in logs
    ts = time.time()
    ts_date = datetime.fromtimestamp(ts).strftime('%Y-%b-%d-%H-%M-%S')
    log_info = [{
        'description': 'data_send_to_node',
        'ts': ts,
        'ts_date': ts_date,
        'worker': args.host
    }]
    filename = os.path.join(args.log_dir, f'{ts_date}-{args.dataset}-logging-{args.host}.json')

    with open(filename, 'w') as file:
        json.dump(log_info, file, indent=2)

    # sleeper
    print(f'Providing data for {args.lifespan} minutes ...')
    time.sleep(args.lifespan * 60)


if __name__ == "__main__":
    args = Arguments()
    print(
        '### Openmined Data Provider ###',
        'Data path: {}'.format(args.data_path),
        'Using node: {}'.format(args.node_addr),
        'Experiment tag: {}'.format(args.exp_tag),
        sep='\n'
    )
    main(args)