import os
import glob
from datetime import timedelta

from airflow.operators.python_operator import PythonOperator
from airflow.utils.decorators import apply_defaults
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project


class KaapanaPythonBaseOperator(PythonOperator):
    def __init__(
        self,
        dag,
        name,
        python_callable,
        operator_out_dir=None,
        input_operator=None,
        task_id=None,
        parallel_id=None,
        keep_parallel_id=True,
        trigger_rule='all_success',
        retries=1,
        retry_delay=timedelta(seconds=30),
        execution_timeout=timedelta(minutes=30),
        task_concurrency=None,
        pool=None,
        pool_slots=None,
        ram_mem_mb=100,
        ram_mem_mb_lmt=None,
        cpu_millicores=None,
        cpu_millicores_lmt=None,
        gpu_mem_mb=None,
        gpu_mem_mb_lmt=None,
        manage_cache=None,
        *args, **kwargs
    ):

        KaapanaBaseOperator.set_defaults(
            self,
            name=name,
            task_id=task_id,
            operator_out_dir=operator_out_dir,
            input_operator=input_operator,
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
            manage_cache=manage_cache
        )

        super().__init__(
            dag=dag,
            python_callable=python_callable,
            task_id=self.task_id,
            trigger_rule=self.trigger_rule,
            provide_context=True,
            retry_delay=retry_delay,
            retries=retries,
            task_concurrency=task_concurrency,
            execution_timeout=execution_timeout,
            executor_config=self.executor_config,
            pool=self.pool,
            pool_slots=self.pool_slots,
            *args,
            **kwargs
        )

    def post_execute(self, context, result=None):
        pass
