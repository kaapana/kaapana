import os
import torch as th

from experiments.exp_mnist import FedExp_MNIST
#from experiments.exp_chest_xray import FedExp_ChestXray


class Arguments():
    def __init__(self):
        self.experiment = os.getenv('EXPERIMENT', 'mnist_exp')
        self.save_model = (os.getenv('SAVE_MODEL', 'False') == 'True')
        self.out_dir = os.getenv('OPERATOR_OUT_DIR', '/models/trained')
        
        self.grid_host = os.getenv('GRID_HOST', '10.128.129.76')
        self.grid_port = os.getenv('GRID_PORT', '7000')


def main(args):

    # define experiment
    if args.experiment == 'mnist_exp':
        experiment = FedExp_MNIST(grid_host=args.grid_host,grid_port=args.grid_port)
    elif args.experiment == 'chestxray_exp':
        experiment = None
        #experiment = FedExp_ChestXray(grid_host=args.grid_host,grid_port=args.grid_port)
    else:
        experiment = None
    assert (experiment is not None),\
        "Failed to create experiment (check given exp_arg: '{}')- Stopping!".format(args.experiment)
    
    # run experiment
    experiment.run_experiment()

    # shut down data provider
    experiment.shutdown_data_providers()

    # save trained model
    experiment.save_model(
        save_model=args.save_model,
        model_name='mnist',
        out_dir=args.out_dir
        )


if __name__ == "__main__":
    args = Arguments()
    main(args)