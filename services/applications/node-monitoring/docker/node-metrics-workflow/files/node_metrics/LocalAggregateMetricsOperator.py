from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from os.path import join, exists, dirname, basename
import os
from glob import glob

class LocalAggregateMetricsOperator(KaapanaPythonBaseOperator):
    def start(self, ds, **kwargs):
        print("Start LocalGetMetricsOperator ...")

        run_dir = join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        aggregated_metrics_output_dir_path = join(run_dir, self.batch_name, self.operator_out_dir,"aggregated_metris.txt")
        os.makedirs(dirname(aggregated_metrics_output_dir_path), exist_ok=True)

        with open(aggregated_metrics_output_dir_path,"w") as aggregated_rest:
            for metric_input_dir in self.input_dirs:
                component_input_dir = join(
                    self.airflow_workflow_dir, kwargs["dag_run"].run_id,self.batch_name, metric_input_dir
                )
                print(f" Searching in componend-dir: {component_input_dir}")
                assert exists(component_input_dir)

                txt_files = glob(join(component_input_dir, "*.txt*"))
                print(f" Found {len(txt_files)} metric txt-files")

                for txt_file in txt_files:
                    aggregated_rest.write(f"job_name: {basename(txt_file).split('.')[0]}\n")
                    print(f"Prepare metrics from: {txt_file}")
                    with open(txt_file) as file:
                        for line in file:
                            aggregated_rest.write(line)

    def __init__(self, dag, metrics_operators, **kwargs):
        self.input_dirs = [x.operator_out_dir for x in metrics_operators]
        super().__init__(
            dag=dag, name="aggregate-metrics", python_callable=self.start, **kwargs
        )
