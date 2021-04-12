import os
import glob
from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class ExpSchedulerOperatorMNIST(KaapanaBaseOperator):

    @staticmethod
    def on_success(info_dict):
        print("##################################################### on_success!")
        pod_id = info_dict["ti"].task.kube_name
        print("--> federated training ended, now delete pod {} !".format(pod_id))
        KaapanaBaseOperator.pod_stopper.stop_pod_by_name(pod_id=pod_id)
    
    def execute(self, context):
        self.env_vars['RUN_ID'] = context['run_id']
        return super().execute(context)
    
    def __init__(self,
                 dag,
                 scheduler=None,
                 procedure=None,
                 participants=None,
                 env_vars=None,
                 execution_timeout=timedelta(hours=6),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}
        
        envs = {
            "PROCEDURE": str(procedure),
            "SCHEDULER": str(scheduler),
            "PARTICIPANTS": participants
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            name="training-scheduler",
            image="{}{}/federated-exp-mnist:0.1.0-vdev".format(default_registry, default_project),
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            on_success_callback=ExpSchedulerOperatorMNIST.on_success,
            execution_timeout=execution_timeout,
            training_operator=True,
            image_pull_policy='Always',
            *args, **kwargs
            )