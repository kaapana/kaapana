import os
import glob
import functools
from datetime import timedelta

from airflow.operators.python import PythonOperator
from airflow.models.skipmixin import SkipMixin
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, kaapana_build_version

def rest_self_udpate(func):
    '''
    Every operator which should be adjustable from an api call should add this as an decorator above the python_callable:
    @rest_self_udpate
    '''
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if kwargs["dag_run"] is not None and kwargs["dag_run"].conf is not None and 'rest_call' in kwargs["dag_run"].conf and kwargs["dag_run"].conf['rest_call'] is not None:
            payload = kwargs["dag_run"].conf['rest_call']
            operator_conf = {}
            if 'operators' in payload and self.name in payload['operators']:
                operator_conf.update(payload['operators'][self.name])
            if 'global' in payload:
                operator_conf.update(payload['global'])
   
            for k, v in operator_conf.items():
                if k in self.__dict__.keys():
                    self.__dict__[k] = v

        return func(self, *args, **kwargs)
    return wrapper

class KaapanaPythonBaseOperator(PythonOperator, SkipMixin):
    def __init__(
        self,
        dag,
        name,
        python_callable,
        operator_out_dir=None,
        input_operator=None,
        operator_in_dir=None,
        task_id=None,
        parallel_id=None,
        keep_parallel_id=True,
        trigger_rule='all_success',
        retries=1,
        retry_delay=timedelta(seconds=30),
        execution_timeout=timedelta(minutes=30),
        max_active_tis_per_dag=None,
        pool=None,
        pool_slots=None,
        ram_mem_mb=100,
        ram_mem_mb_lmt=None,
        cpu_millicores=None,
        cpu_millicores_lmt=None,
        gpu_mem_mb=None,
        gpu_mem_mb_lmt=None,
        manage_cache=None,
        allow_federated_learning=False,
        whitelist_federated_learning=None,
        delete_input_on_success=False,
        delete_output_on_start=True,
        batch_name=None,
        airflow_workflow_dir=None,
        **kwargs
    ):

        KaapanaBaseOperator.set_defaults(
            self,
            name=name,
            task_id=task_id,
            operator_out_dir=operator_out_dir,
            input_operator=input_operator,
            operator_in_dir=operator_in_dir,
            parallel_id=parallel_id,
            keep_parallel_id=keep_parallel_id,
            trigger_rule=trigger_rule,
            pool=pool,
            pool_slots=pool_slots,
            ram_mem_mb=ram_mem_mb,
            ram_mem_mb_lmt=ram_mem_mb_lmt,
            cpu_millicores=cpu_millicores,
            cpu_millicores_lmt=cpu_millicores_lmt,
            gpu_mem_mb=gpu_mem_mb,
            gpu_mem_mb_lmt=gpu_mem_mb_lmt,
            manage_cache=manage_cache,
            allow_federated_learning=allow_federated_learning,
            whitelist_federated_learning=whitelist_federated_learning,
            batch_name=batch_name,
            airflow_workflow_dir=airflow_workflow_dir,
            delete_input_on_success=delete_input_on_success,
            delete_output_on_start=delete_output_on_start
        )

        super().__init__(
            dag=dag,
            python_callable=python_callable,
            task_id=self.task_id,
            trigger_rule=self.trigger_rule,
            provide_context=True,
            retry_delay=retry_delay,
            retries=retries,
            max_active_tis_per_dag=max_active_tis_per_dag,
            execution_timeout=execution_timeout,
            executor_config=self.executor_config,
            on_success_callback=KaapanaBaseOperator.on_success,
            pool=self.pool,
            pool_slots=self.pool_slots,
            **kwargs
        )

    def post_execute(self, context, result=None):
        pass
