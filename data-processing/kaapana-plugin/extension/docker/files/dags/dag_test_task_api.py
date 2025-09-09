from airflow.models import DAG
from kaapana.operators.KaapanaTaskOperator import KaapanaTaskOperator

with DAG("test-task-dag") as dag:
    task = KaapanaTaskOperator(
        task_id="dummy",
        image="registry.hzdr.de/lorenz.feineis/kaapana-feineis-dev/dummy:latest",
        taskTemplate="default",
    )
