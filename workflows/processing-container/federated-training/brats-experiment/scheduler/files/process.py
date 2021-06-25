import os
import json
import time
import shutil
from datetime import datetime, timedelta

from monai.networks.nets import UNet
from monai.utils import set_determinism

import torch

from utilities import (
    average_model_state_dicts,
    save_checkpoint,
    save_checkpoints_before_avg,
    update_model_and_optimizer
)


class Arguments():
    def __init__(self):
        
        # control what is done in this script
        self.initialize_model = (os.environ.get('INIT_MODEL', 'False') == 'True')
        self.inference = (os.environ.get('INFERENCE', 'False') == 'True')
        self.procedure = os.environ.get('PROCEDURE')
        
        self.workflow_dir = os.environ['WORKFLOW_DIR']
        
        # model where processed/averaged model is saved
        self.model_dir = os.path.join(os.environ['WORKFLOW_DIR'], 'model')
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
        
        # directory where incoming models are saved (by workers)
        self.model_cache = os.path.join(os.environ['WORKFLOW_DIR'], 'cache')
        if not os.path.exists(self.model_cache):
            os.makedirs(self.model_cache)
        
        # local directory for model checkpoints
        self.checkpoints_dir = os.path.join(os.environ['WORKFLOW_DIR'], 'checkpoints')
        if not os.path.exists(self.checkpoints_dir):
            os.makedirs(self.checkpoints_dir)
        
        # timestamp logging
        self.logging = '/models/logging'
        if not os.path.exists(self.logging):
            os.makedirs(self.logging)
        
        # data with test data (i.e for global inference)
        if self.inference:
            self.data_dir = os.path.join(os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])
        
        # federated training
        self.fed_rounds_total = os.environ['FED_ROUNDS_TOTAL']
        self.fed_round = int(os.environ['FED_ROUND']) if os.environ['FED_ROUND'] != 'None' else 0
        self.participants = json.loads('{}'.format(os.environ["PARTICIPANTS"].replace("'", '"'))) if os.environ["PARTICIPANTS"] != 'None' else None # enabels to parse a list as env
        
        self.worker = os.environ['WORKER']
        if self.procedure == 'seq' and self.worker == 'None':
            self.worker = self.participants[0]

        # training parameters
        self.lr_initial = float(os.environ['LEARNING_RATE']) if os.environ['LEARNING_RATE'] != 'None' else 1e-4
        self.wdecay_initial = float(os.environ['WEIGHT_DECAY']) if os.environ['WEIGHT_DECAY'] != 'None' else 1e-5

        self.seed = int(os.environ['SEED']) if os.environ['SEED'] != 'None' else None


def initialize_model(args):
    """Reads given lr and creates intial model"""
    
    # initialize model
    model = UNet(
        dimensions=3,
        in_channels=4,
        out_channels=3,
        channels=(16, 32, 64, 128, 256),
        strides=(2, 2, 2, 2),
        num_res_units=2,
    )
    optimizer = torch.optim.Adam(
        model.parameters(), args.lr_initial, weight_decay=args.wdecay_initial, amsgrad=True
    )
    print('Model initialization! (learning rate: {} | weight decay: {})'.format(args.lr_initial, args.wdecay_initial))

    # saving initial model
    model_checkpoint = {
        'model': model.state_dict(),
        'optimizer': optimizer.state_dict()
    }
    print('Saving initial model for further processing')
    torch.save(model_checkpoint, os.path.join(args.model_dir, 'model_checkpoint.pt'))
    print('Saving initial model to checkpoints directory')
    torch.save(model_checkpoint, os.path.join(args.checkpoints_dir, '{}-checkpoint_initial.pt'.format(time.strftime("%Y%m%d-%H%M%S"))))

    # save timestamp log
    filename = os.path.join(args.logging, 'federated_exp_logging.json')
    ts_date_init = datetime.now() + timedelta(hours=2)
    log_entry = {
            'description': 'init',
            'fed_round': args.fed_round,
            'ts': ts_date_init,
            'ts_date': ts_date_init.strftime('%Y-%b-%d-%H-%M-%S')
        }
    logs = []
    logs.append(log_entry)

    with open(filename, 'w') as file:
        json.dump(logs, file, indent=2)
    print('Saved initialization timestamp!')


def inference(args):
    raise NotImplementedError
        

def main(args):

    # clear cache (airflow dir) - Done to not carry on all checkpoints - they are saved in Minio anyways
    shutil.rmtree(args.checkpoints_dir)
    if not os.path.exists(args.checkpoints_dir):
        os.makedirs(args.checkpoints_dir)


    #### Model processing - Sequential Training ###
    if args.procedure == 'seq':
        print('#'*50, 'Sequential training - worker: {} round: {}/{}'.format(args.worker, args.fed_round, args.fed_rounds_total))
        
        # load recieved model
        print('Loading model recieved from worker: {}'.format(args.worker))
        checkpoint = torch.load('{}/model_checkpoint_from_{}.pt'.format(args.model_cache, args.worker))
        model_state_dict, optimizer_state_dict = checkpoint['model'], checkpoint['optimizer']
        
        model, optimizer = update_model_and_optimizer(args, model_state_dict, optimizer_state_dict)

        # save averaged model state
        save_checkpoint(args, model, optimizer)

    
    #### Model processing - Averaging ###
    elif args.procedure == 'avg':
        print('#'*50, 'Averaging recieved models - round {}/{}'.format(args.fed_round, args.fed_rounds_total))
        
        # get file paths of received models and save the models as backups
        model_file_list = [f'{args.model_cache}/model_checkpoint_from_{participant}.pt' for participant in args.participants]
        #save_checkpoints_before_avg(args, model_file_list) # <-- not really needed since (best) models are saved on the participants sites
        
        # get state dicts of received models
        model_state_dicts = [torch.load(model)['model'] for model in model_file_list]

        # average models to new model
        print('Apply averaging on ({}) models: {}'.format(len(model_file_list) ,model_file_list))
        model_state_dict_avg = average_model_state_dicts(model_state_dicts)

        # load an optimizer state dict (TODO: Average or hard code, which means reset?)
        optimizer_state_dict = torch.load(model_file_list[0])['optimizer']
        
        model, optimizer = update_model_and_optimizer(args, model_state_dict_avg, optimizer_state_dict)

        # save checkpoint
        save_checkpoint(args, model, optimizer)
    
    else:
        raise AssertionError('Procedure needs to be set either "avg" or "seq"')


if __name__ == '__main__':
    args = Arguments()
    set_determinism(seed=args.seed)
    print(
        '########### FL Scheduler for Exp. on BraTS data ###########',
        'Deterministic: {}'.format(args.seed),
        sep='\n'
    )

    if args.initialize_model:
        initialize_model(args)
    elif args.inference:
        inference(args)
    else:
        main(args)
