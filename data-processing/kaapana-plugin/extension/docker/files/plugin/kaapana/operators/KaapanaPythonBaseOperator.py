from datetime import timedelta

from airflow.models.skipmixin import SkipMixin
from airflow.operators.python import PythonOperator
from kaapana.operators import HelperSendEmailService
from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


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
        trigger_rule="all_success",
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
        priority_class_name=None,
        display_name="-",
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
            delete_output_on_start=delete_output_on_start,
            priority_class_name=priority_class_name,
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
            on_failure_callback=KaapanaPythonBaseOperator.on_failure,
            pool=self.pool,
            pool_slots=self.pool_slots,
            **kwargs
        )

        self.display_name = display_name

    def post_execute(self, context, result=None):
        pass

    @staticmethod
    def on_failure(context):
        send_email_on_workflow_failure = context["dag_run"].dag.default_args.get(
            "send_email_on_workflow_failure", False
        )
        if send_email_on_workflow_failure:
            HelperSendEmailService.handle_task_failure_alert(context)
        send_notification_on_workflow_failure = context["dag_run"].dag.default_args.get(
            "send_notification_on_workflow_failure", False
        )
        if send_notification_on_workflow_failure:
            KaapanaBaseOperator.post_notification_to_user_from_context(context)
