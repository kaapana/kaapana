import os
import numpy as np

from monai.apps import DecathlonDataset
from monai.config import print_config
from monai.data import DataLoader
from monai.losses import DiceLoss
from monai.metrics import DiceMetric
from monai.networks.nets import UNet
from monai.transforms import (
    Activations,
    AsDiscrete,
    Compose,
)
from monai.utils import set_determinism

import torch
from torch.utils.tensorboard import SummaryWriter

from utilities import TRAIN_TRANSFORM, VAL_TRANSFORM

print('#'*46)
print_config()
print('#'*46)


class Arguments():
    def __init__(self):
        '''Set args from envs given by Airflow operator'''
        
        self.root_dir = os.path.join(os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])

        self.logs_dir = os.path.join(os.environ['WORKFLOW_DIR'], 'logs')

        self.model_dir = os.path.join(os.environ['WORKFLOW_DIR'], 'model')
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
        
        self.model_cache = os.path.join(os.environ['WORKFLOW_DIR'], 'cache')
        if not os.path.exists(self.model_cache):
            os.makedirs(self.model_cache)
        
        self.checkpoints_dir = os.path.join(os.environ['WORKFLOW_DIR'], 'checkpoints')
        if not os.path.exists(self.checkpoints_dir):
            os.makedirs(self.checkpoints_dir)

        self.num_wokers = 4
        self.batch_size = int(os.environ['BATCH_SIZE'])
        self.val_interval = int(os.environ['VAL_INTERVAL'])
        self.validation = (os.environ.get('VALIDATION', 'False') == 'True')
        self.return_best_model = (os.environ.get('RETURN_BEST_MODEL', 'False') == 'True')

        self.n_epochs = int(os.environ['N_EPOCHS'])
        self.fed_round = int(os.environ['FED_ROUND']) if os.environ['FED_ROUND'] != 'None' else 0
        self.epoch = (self.fed_round * self.n_epochs)

        self.host_ip = os.environ['HOST_IP']
        self.verbose = (os.environ.get('VALIDATION', 'False') == 'True')
        self.seed = int(os.environ['SEED']) if os.environ['SEED'] != 'None' else None


def run_training(args, model, train_loader, val_loader, optimizer, device, tb_logger):
    """
    Complete training including performance validation
    """

    max_epochs = args.n_epochs
    val_interval = args.val_interval
    
    best_metric = -1
    best_metric_epoch = -1
    epoch_loss_values = []
    metric_values = []
    metric_values_tc = []
    metric_values_wt = []
    metric_values_et = []

    loss_function = DiceLoss(to_onehot_y=False, sigmoid=True, squared_pred=True)
    
    print('#'*10, 'Start training!', '#'*10)
    for epoch in range(max_epochs):
        print("-" * 10)
        print(f"epoch {epoch + 1}/{max_epochs}")
        model.train()
        epoch_loss = 0
        step = 0
        for batch_data in train_loader:
            step += 1
            inputs, labels = (
                batch_data["image"].to(device),
                batch_data["label"].to(device),
            )
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = loss_function(outputs, labels)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()            
            if args.verbose:
                print(
                    f"{step}/{len(train_loader.dataset) // train_loader.batch_size}"
                    f", train_loss: {loss.item():.4f}"
                )
        epoch_loss /= step
        epoch_loss_values.append(epoch_loss)
        print(f"epoch {epoch + 1} average loss: {epoch_loss:.4f}")
        # tensorboard logging
        tb_logger.add_scalar("Loss (train)", epoch_loss, epoch)

        if (epoch + 1) % val_interval == 0:
            model.eval()
            with torch.no_grad():
                dice_metric = DiceMetric(include_background=True, reduction="mean")
                post_trans = Compose(
                    [Activations(sigmoid=True), AsDiscrete(threshold_values=True)]
                )
                metric_sum = metric_sum_tc = metric_sum_wt = metric_sum_et = 0.0
                metric_count = (
                    metric_count_tc
                ) = metric_count_wt = metric_count_et = 0
                for val_data in val_loader:
                    val_inputs, val_labels = (
                        val_data["image"].to(device),
                        val_data["label"].to(device),
                    )
                    val_outputs = model(val_inputs)
                    val_outputs = post_trans(val_outputs)
                    # compute overall mean dice
                    value, not_nans = dice_metric(y_pred=val_outputs, y=val_labels)
                    not_nans = not_nans.item()
                    metric_count += not_nans
                    metric_sum += value.item() * not_nans
                    # compute mean dice for TC
                    value_tc, not_nans = dice_metric(
                        y_pred=val_outputs[:, 0:1], y=val_labels[:, 0:1]
                    )
                    not_nans = not_nans.item()
                    metric_count_tc += not_nans
                    metric_sum_tc += value_tc.item() * not_nans
                    # compute mean dice for WT
                    value_wt, not_nans = dice_metric(
                        y_pred=val_outputs[:, 1:2], y=val_labels[:, 1:2]
                    )
                    not_nans = not_nans.item()
                    metric_count_wt += not_nans
                    metric_sum_wt += value_wt.item() * not_nans
                    # compute mean dice for ET
                    value_et, not_nans = dice_metric(
                        y_pred=val_outputs[:, 2:3], y=val_labels[:, 2:3]
                    )
                    not_nans = not_nans.item()
                    metric_count_et += not_nans
                    metric_sum_et += value_et.item() * not_nans

                metric = metric_sum / metric_count
                metric_values.append(metric)
                metric_tc = metric_sum_tc / metric_count_tc
                metric_values_tc.append(metric_tc)
                metric_wt = metric_sum_wt / metric_count_wt
                metric_values_wt.append(metric_wt)
                metric_et = metric_sum_et / metric_count_et
                metric_values_et.append(metric_et)
                if metric > best_metric:
                    best_metric = metric
                    best_metric_epoch = epoch + 1                    
                    # save best model to local checkpoints directory
                    save_model(args, model, optimizer)
                    print("Saved new best metric model")
                print(
                    f"current epoch: {epoch + 1} current mean dice: {metric:.4f}"
                    f" tc: {metric_tc:.4f} wt: {metric_wt:.4f} et: {metric_et:.4f}"
                    f"\nbest mean dice: {best_metric:.4f}"
                    f" at epoch: {best_metric_epoch}"
                )
                # tensorboard logging
                tb_logger.add_scalar("Val Mean Dice", epoch_loss, epoch)
                tb_logger.add_scalar("Val Mean Dice (TC)", epoch_loss, epoch)
                tb_logger.add_scalar("Val Mean Dice (WT)", epoch_loss, epoch)
                tb_logger.add_scalar("Val Mean Dice (ET)", epoch_loss, epoch)


    print(f"Training completed, best_metric: {best_metric:.4f}  at epoch: {best_metric_epoch}")

    if not args.return_best_model:
        save_model(args, model, optimizer, final=True)
        print("Saved final model after training all epochs")
    else:
        print(f"Best model was saved at epoch {best_metric_epoch}")


def save_model(args, model, optimizer, final=False):
    """Saves model & optimizer as checkpoint either to send back """
    
    model_checkpoint = {
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict()
    }
    if final:
        file_path = os.path.join(args.model_cache, 'model_checkpoint_from_{}.pt'.format(args.host_ip))
    else:
        file_path = os.path.join(args.checkpoints_dir, 'model_checkpoint_from_{}_round_{}.pt'.format(args.host_ip, args.fed_round))
    torch.save(model_checkpoint, file_path)


def prepare_data_loader(args):
    print('Start preparing data loaders...')
    
    train_dataset = DecathlonDataset(
        root_dir=args.root_dir,
        task="Task01_BrainTumour",
        transform=TRAIN_TRANSFORM,
        section="training",
        download=False,
        num_workers=4,
        cache_num=100,
    )
    train_loader = DataLoader(train_dataset, batch_size=2, shuffle=True, num_workers=4)

    val_dataset = DecathlonDataset(
        root_dir=args.root_dir,
        task="Task01_BrainTumour",
        transform=VAL_TRANSFORM,
        section="validation",
        download=False,
        num_workers=4,
    )
    val_loader = DataLoader(val_dataset, batch_size=2, shuffle=False, num_workers=4)
    print('Finished preparing data loaders...')

    return train_loader, val_loader


def prepare_model_and_optimizer():
    """Loads model/optimizer received from scheduler"""

    checkpoint = torch.load(os.path.join(args.model_dir, 'model_checkpoint.pt'))

    model = UNet(
        dimensions=3,
        in_channels=4,
        out_channels=3,
        channels=(16, 32, 64, 128, 256),
        strides=(2, 2, 2, 2),
        num_res_units=2,
    )
    model.load_state_dict(checkpoint['model'])

    optimizer = torch.optim.Adam(
        model.parameters(), 1e-4, weight_decay=1e-5, amsgrad=True
    ) # <-- values are overwritten in next step
    optimizer.load_state_dict(checkpoint['optimizer'])

    return model, optimizer


def check_for_cuda():
    if torch.cuda.is_available():
        device = torch.device('cuda')
        print('Using device: {}'.format(device))
    else:
        raise Exception ('Cuda is not available!')
    return device


def main(args):

    # logging
    tb_logger = SummaryWriter(
        log_dir='{}/participant-{}'.format(args.logs_dir, args.host_ip),
        filename_suffix='-fed_round_{}'.format(args.fed_round)
    )

    # check if cuda is available    
    device = check_for_cuda()

    # load model & optimizer received from scheduler
    model, optimizer = prepare_model_and_optimizer()
    model.to(device)

    # dataloader
    train_loader, val_loader = prepare_data_loader(args)

    # run model training & validation
    run_training(args, model, train_loader, val_loader, optimizer, device, tb_logger)

    tb_logger.flush()


if __name__ == '__main__':
    args = Arguments()
    set_determinism(seed=args.seed)
    print(
        '########### Training on BraTS data ###########',
        'Deterministic: {}'.format(args.seed),
        'Return best model: {}'.format(args.return_best_model),
        sep='\n'
    )
    main(args)
