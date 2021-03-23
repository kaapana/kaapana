from datetime import timedelta, datetime
import os
import uuid
from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume

from kaapana.operators.KaapanaApplicationOperator import KaapanaApplicationOperator

class RunNodeOperator(KaapanaApplicationOperator):

    def __init__(self,
                    dag,
                    global_id=None,
                    hostname=None,
                    port=None,
                    grid_network_url=None,
                    sets=None,
                    release_name=None,
                    execution_timeout=timedelta(hours=6),
                    *args, **kwargs
                    ):

        if sets is None:
            sets = {}

        sets_vars = {
            'global.id': global_id,
            'hostname': hostname,
            'port': port,
            'grid_network_url': grid_network_url
        }

        sets.update(sets_vars)

        super(RunNodeOperator, self).__init__(
            dag=dag,
            name="openmined-node",
            chart_name="openmined-grid-node-chart",
            version="0.1.0-vdev",
            release_name=release_name,
            sets=sets,
            *args, **kwargs
            )