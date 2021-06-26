import os
import json
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

from utilities import (
    save_model,
    check_for_cuda,
    prepare_model_and_optimizer,
    prepare_data_loader
)

print('#'*46)
print_config()
print('#'*46)


class Arguments():
    def __init__(self):
        '''Set args from envs given by Airflow operator'''
        
        self.root_dir = os.path.join(os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])

        # logging
        self.tb_logging = os.path.join(os.environ['WORKFLOW_DIR'], 'logs') # <- will be send to scheduler

        self.logging = '/models/logging'
        if not os.path.exists(self.logging):
            os.makedirs(self.logging)
        
        # contains global model received from scheduler
        self.model_dir = os.path.join(os.environ['WORKFLOW_DIR'], 'model')
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
        
        # saves trained model - will be send to scheduler
        self.model_cache = os.path.join(os.environ['WORKFLOW_DIR'], 'cache')
        if not os.path.exists(self.model_cache):
            os.makedirs(self.model_cache)
        
        # saves checkpoint into local minio
        self.checkpoints_dir = os.path.join(os.environ['WORKFLOW_DIR'], 'checkpoints')
        if not os.path.exists(self.checkpoints_dir):
            os.makedirs(self.checkpoints_dir)

        self.num_wokers = 4
        self.batch_size = int(os.environ['BATCH_SIZE'])
        self.val_interval = int(os.environ['VAL_INTERVAL'])
        self.validation = (os.environ.get('VALIDATION', 'False') == 'True')

        self.n_epochs = int(os.environ['N_EPOCHS'])
        self.fed_round = int(os.environ['FED_ROUND']) if os.environ['FED_ROUND'] != 'None' else 0
        self.epoch = (self.fed_round * self.n_epochs)

        self.host_ip = os.environ['HOST_IP']
        self.verbose = (os.environ.get('VALIDATION', 'False') == 'True')
        self.seed = int(os.environ['SEED']) if os.environ['SEED'] != 'None' else None

        self.lr = float(os.environ['LEARNING_RATE'])
        self.weight_decay = float(os.environ['WEIGHT_DECAY'])


def run_training(args, model, train_loader, val_loader, optimizer, device, tb_logger):
    """Complete training including performance validation during training"""

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
        
        # Epoch logging
        print(f"epoch {epoch + 1} average loss: {epoch_loss:.4f}")
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

    # save model after training all epochs
    save_model(args, model, optimizer, final=True)
    print("Saved final model after training all epochs")


def train(args, model, train_loader, optimizer, device, tb_logger):
    """Training without validation during training"""

    # read in train logs
    filename_epoch_loss = os.path.join(args.logging, 'brats_exp_epoch_loss_logging_{}.json'.format(args.host_ip))
    epoch_loss_logs = [] if args.fed_round == 0 else json.load(open(filename_epoch_loss))
    
    filename_step_loss = os.path.join(args.logging, 'brats_exp_step_loss_logging_{}.json'.format(args.host_ip))
    step_loss_logs = [] if args.fed_round == 0 else json.load(open(filename_step_loss))
    
    # Training
    max_epochs = args.n_epochs
    loss_function = DiceLoss(to_onehot_y=False, sigmoid=True, squared_pred=True)
    
    print(
        "########## Start training! ##########",
        f"Starting with epoch: {args.epoch}",
        f"Train for {args.n_epochs} epochs",
        sep="\n"
    )
    
    for epoch in range(args.epoch, args.epoch + args.n_epochs):
        print("-" * 10)
        print(f"Epoch: {epoch}")
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
            
            global_step = len(step_loss_logs)
            
            # Step logging
            if args.verbose:
                print(
                    f"{step}/{len(train_loader.dataset) // train_loader.batch_size}"
                    f", train_loss: {loss.item():.4f}"
                )
            tb_logger.add_scalar("Loss_Training_Steps", loss.item(), global_step)

            # log to file
            log_entry = {
                'step': global_step,
                'loss': loss.item(),
                'fed_round': args.fed_round,
                'epoch': epoch,
                'participant': args.host_ip
            }
            step_loss_logs.append(log_entry)
            
            with open(filename_step_loss, 'w') as file:
                json.dump(step_loss_logs, file, indent=2)

        epoch_loss /= step
        
        # Epoch logging
        print(f"epoch {epoch} average loss: {epoch_loss:.4f}")
        tb_logger.add_scalar("Loss_Training_Epochs", epoch_loss, epoch)
        
        # log to file
        log_entry = {
            'loss': epoch_loss,
            'fed_round': args.fed_round,
            'epoch': epoch,
            'participant': args.host_ip
        }
        epoch_loss_logs.append(log_entry)

        with open(filename_epoch_loss, 'w') as file:
            json.dump(epoch_loss_logs, file, indent=2)
        
    # save model after training all epochs
    save_model(args, model, optimizer, final=True)
    print("Saved model after training all epochs")


def validate_global_model(args, model, val_loader, device, tb_logger):
    """Validation of global model on locally available validataion data"""

    # read in val logs
    filename_val_logs = os.path.join(args.logging, 'brats_exp_validation_logging_{}.json'.format(args.host_ip))
    val_logs = [] if args.fed_round == 0 else json.load(open(filename_val_logs))

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

        # iterate over validation data
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
        #metric_values.append(metric)
        metric_tc = metric_sum_tc / metric_count_tc
        #metric_values_tc.append(metric_tc)
        metric_wt = metric_sum_wt / metric_count_wt
        #metric_values_wt.append(metric_wt)
        metric_et = metric_sum_et / metric_count_et
        #metric_values_et.append(metric_et)
        
        print(
            "########################################################",
            "Global model performance on local validation data:",
            f"Federated round: {args.fed_round}",
            f"current mean dice: {metric:.4f}",
            f"tc: {metric_tc:.4f}",
            f"wt: {metric_wt:.4f}",
            f"et: {metric_et:.4f}",
            #f"\nbest mean dice: {best_metric:.4f}",
            #f" at epoch: {best_metric_epoch}",
            "########################################################",
            sep='\n'
            )
        
        # Tensorboard logging
        tb_logger.add_scalar("Val_Mean_Dice", metric, args.fed_round)
        tb_logger.add_scalar("Val_Mean_Dice (TC)", metric_tc, args.fed_round)
        tb_logger.add_scalar("Val_Mean_Dice (WT)", metric_wt, args.fed_round)
        tb_logger.add_scalar("Val_Mean_Dice (ET)", metric_et, args.fed_round)

        # write to validation logs
        log_entry = {
            'fed_round': args.fed_round,
            'mean_dice': metric,
            'mean_dice_tc': metric_tc,
            'mean_dice_wt': metric_wt,
            'mean_dice_et': metric_et,
            'participant': args.host_ip
        }
        val_logs.append(log_entry)

        with open(filename_val_logs, 'w') as file:
            json.dump(val_logs, file, indent=2)


def main(args):

    # logging
    tb_logger = SummaryWriter(
        log_dir='{}/participant-{}'.format(args.tb_logging, args.host_ip),
        filename_suffix='-fed_round_{}'.format(args.fed_round)
    )

    # check if cuda is available    
    device = check_for_cuda()

    # load model & optimizer received from schedulers (model is send to device, cuda)
    model, optimizer = prepare_model_and_optimizer(args, device)

    # get dataloader
    train_loader, val_loader = prepare_data_loader(args)

    # Validate global models performance on local test data
    validate_global_model(args, model, val_loader, device, tb_logger)

    # run training on local train-data (no additional validation)
    train(args, model, train_loader, optimizer, device, tb_logger)

    # run model training & validation
    #run_training(args, model, train_loader, val_loader, optimizer, device, tb_logger)

    tb_logger.flush()


if __name__ == '__main__':
    args = Arguments()
    set_determinism(seed=args.seed)
    print(
        '########### Training on BraTS data ###########',
        'Deterministic: {}'.format(args.seed),
        sep='\n'
    )
    main(args)
