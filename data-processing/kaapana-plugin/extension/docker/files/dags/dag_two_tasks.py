from airflow.models import DAG
from kaapana.operators.KaapanaTaskOperator import KaapanaTaskOperator, IOMapping


with DAG("test-two-tasks") as dag:
    task = KaapanaTaskOperator(
        task_id="dummy",
        image="registry.hzdr.de/lorenz.feineis/kaapana-feineis-dev/dummy-task:0.0.0-latest",
        taskTemplate="upstream",
    )

    downstream = KaapanaTaskOperator(
        task_id="downstream",
        image="registry.hzdr.de/lorenz.feineis/kaapana-feineis-dev/dummy-task:0.0.0-latest",
        taskTemplate="downstream",
        iochannel_maps=[
            IOMapping(
                upstream_operator=task,
                upstream_channel="channel1",
                downstream_channel="channel1",
            ),
            IOMapping(
                upstream_operator=task,
                upstream_channel="channel2",
                downstream_channel="channel2",
            ),
        ],
    )

    task >> downstream
