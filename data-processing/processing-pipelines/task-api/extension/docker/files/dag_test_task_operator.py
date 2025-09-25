from airflow.models import DAG
from task_api_operator.KaapanaTaskOperator import KaapanaTaskOperator, IOMapping


from kaapana.blueprints.kaapana_global_variables import (
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
)


args = {
    "ui_visible": True,
    "owner": "kaapana",
}


with DAG("test-task-operator", default_args=args) as dag:
    task = KaapanaTaskOperator(
        task_id="dummy",
        image=f"{DEFAULT_REGISTRY}/dummy:{KAAPANA_BUILD_VERSION}",
        taskTemplate="upstream",
    )

    downstream = KaapanaTaskOperator(
        task_id="downstream",
        image=f"{DEFAULT_REGISTRY}/dummy:{KAAPANA_BUILD_VERSION}",
        taskTemplate="downstream",
        iochannel_maps=[
            IOMapping(
                upstream_operator=task,
                upstream_output_channel="channel1",
                input_channel="channel1",
            ),
            IOMapping(
                upstream_operator=task,
                upstream_output_channel="channel2",
                input_channel="channel2",
            ),
        ],
    )

    task >> downstream
