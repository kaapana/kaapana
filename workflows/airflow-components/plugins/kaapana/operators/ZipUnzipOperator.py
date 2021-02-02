import os
import glob
from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class ZipUnzipOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 target_filename = None,
                 subdir = None,
                 mode = None, # 'zip' or 'unzip'
                 batch_level = False,
                 whitelist_files = None, # eg: "*.txt,*.png" or whole filenames
                 blacklist_files = None, # eg: "*.txt,*.png" or whole filenames
                 env_vars = None,
                 execution_timeout=timedelta(minutes=10),
                 *args, **kwargs
                 ):

        if env_vars is None:
            env_vars = {}

        envs = {
            "TARGET_FILENAME": target_filename if target_filename is not None else "NONE",
            "MODE": mode if mode is not None else "NONE",
            "SUBDIR": subdir if subdir is not None else "NONE",
            "BATCH_LEVEL": str(batch_level),
            "WHITELIST_FILES": whitelist_files if whitelist_files is not None else "NONE",
            "BLACKLIST_FILES": blacklist_files if blacklist_files is not None else "NONE",
        }

        env_vars.update(envs)

        super().__init__(
            dag=dag,
            image="{}{}/zip-unzip:3.0.0".format(default_registry, default_project),
            name="zip-unzip",
            image_pull_secrets=["registry-secret"],
            image_pull_policy="Always",
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            *args, **kwargs
        )
