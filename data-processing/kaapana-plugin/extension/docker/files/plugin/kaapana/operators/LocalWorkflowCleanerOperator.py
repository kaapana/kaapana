import shutil
from pathlib import Path

from kaapana.blueprints.kaapana_utils import get_operator_properties, \
    clean_previous_dag_run
from kaapana.operators.HelperCaching import update_job
from kaapana.operators.KaapanaPythonBaseOperator import \
    KaapanaPythonBaseOperator


class LocalWorkflowCleanerOperator(KaapanaPythonBaseOperator):
    """
    Cleans a local workflow.

    Cleans a local workflow and optionally deleting the workflow directory.
    """

    def start(self, ds, **kwargs):
        run_id, dag_run_dir, dag_run, downstream_tasks = \
            get_operator_properties(self.airflow_workflow_dir, **kwargs)
        conf = dag_run.conf

        clean_previous_dag_run(self.airflow_workflow_dir, conf, 'from_previous_dag_run')
        clean_previous_dag_run(self.airflow_workflow_dir, conf, 'before_previous_dag_run')

        run_dir = dag_run_dir if self.run_dir is None else self.run_dir
        if self.clean_workflow_dir and Path(run_dir).exists():
            print(("Cleaning dir: %s" % run_dir))
            shutil.rmtree(run_dir)
        if conf is not None and 'client_job_id' in conf:
            update_job(
                conf['client_job_id'], status='finished',
                run_id=dag_run.run_id, description=f'Finished successfully'
            )

    def __init__(self,
                 dag,
                 run_dir: str = None,
                 clean_workflow_dir: bool = True,
                 **kwargs):
        """
        :param run_dir: Path to directory of the workflow
        :param clean_workflow_dir: Bool if workflow directory should be deleted
        """

        self.run_dir = run_dir
        self.clean_workflow_dir = clean_workflow_dir

        super().__init__(
            dag=dag,
            name="workflow-cleaner",
            python_callable=self.start,
            **kwargs
        )
