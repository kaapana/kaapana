import os
import time

import syft as sy
from syft.grid.clients.data_centric_fl_client import DataCentricFLClient

import torch
import torchvision
from torchvision import transforms
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

    # wait until node is available
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

    # sleeper
    print(f'Providing data for {args.lifespan} minutes ...')
    time.sleep(args.lifespan * 60)


if __name__ == "__main__":
    args = Arguments()
    print(
        '### Openmined Data Provider ###',
        'Data path: {}'.format(args.data_path),
        'Using node: {}'.format(args.node_addr),
        'Experiment Tag: {}'.format(args.exp_tag),
        sep='\n'
    )
    main(args)