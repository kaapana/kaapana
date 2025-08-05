from airflow.models import DAG
from kaapana.operators.KaapanaTaskOperator import KaapanaTaskOperator

with DAG("test-two-tasks") as dag:
    task = KaapanaTaskOperator(
        task_id="dummy",
        image="registry.hzdr.de/lorenz.feineis/kaapana-feineis-dev/dummy:latest",
    )

    downstream = KaapanaTaskOperator(
        task_id="downstream",
        image="registry.hzdr.de/lorenz.feineis/kaapana-feineis-dev/downstream:latest",
        iochannel_map={"dummy": {"channel1": "channel1", "channel2": "channel2"}},
    )

    task >> downstream
