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
        self.host = os.getenv('NODE_HOST')
        self.port = os.getenv('NODE_PORT', '5000')
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
    dataiter = iter(dataloader)
    images, targets = dataiter.next()

    # wait until node is available
    available = False
    while(not available):
        try:
            node = DataCentricFLClient(hook, args.node_addr)
            available = True
        except:
            time.sleep(5)
    
    # send data to node
    print(f'Sending data to node {args.node_addr}')
    imgs_tag = images.tag('#X', '#dataset', f"#{args.dataset}", args.exp_tag).describe(
        f"images used for experiment {args.exp_tag} ({args.dataset})")
    targets_tag = targets.tag('#Y', '#dataset', f"#{args.dataset}", args.exp_tag).describe(
        f"targets used for experiment {args.exp_tag} ({args.dataset})")

    imgs_ptr, targets_ptr = imgs_tag.send(node), targets_tag.send(node)

    # sleeper
    print(f'Providing data for {args.lifespan} minutes ...')
    time.sleep(args.lifespan * 60)


if __name__ == "__main__":
    args = Arguments()
    main(args)