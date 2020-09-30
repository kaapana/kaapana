from datetime import timedelta, datetime
import os
import uuid
import glob
from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.operators.KaapanaApplicationBaseOperator import KaapanaApplicationBaseOperator

class LocalRunMitk(KaapanaApplicationBaseOperator):

    def __init__(self,
                 dag,
                 name='mitk',
                 data_operator=None,
                 *args,**kwargs
                 ):

        sets = {
            'user': 'mitk',
            'password': 'mitk'
        }

        super().__init__(
            dag=dag,
            name=name,
            chart_name="mitk",
            version="1.0-vdev",
            input_operator=data_operator,
            *args,
            **kwargs)
