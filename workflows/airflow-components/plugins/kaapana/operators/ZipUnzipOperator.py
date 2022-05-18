import os
import glob
from datetime import timedelta

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class ZipUnzipOperator(KaapanaBaseOperator):
    """
    Operator to extract or pack zip archives.

    This operator packs or extracts a set of files using a container. Its execution fails no files have been processed. When extracting it extracts all files provided in the output of its input operator. When packing it packs all files but those extracted and included by a white or blacklist into a single zip file in it's output directory.

    **Inputs:**

    * When packing (e.g. mode is zip) the operator which files should be packed.
    * When extracting (e.g. mode is unzip) nothing.

    **Outputs:**

    * When packing the packed zipfile under the given name.
    * When extracting the extracted files
    """

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
                 **kwargs
                 ):
        """
        :param target_filename: Only for packing. The created file.
        :param subdir: Only for packing. Subdir used to pack, if empty all data are packed.
        :param mode: "zip" for packing "unzip" for extracting
        :param whitelist_files: Only for packing. List of files to include seperated by ',' eg: "*.txt,*.png" or whole filenames
        :param blacklist_files: Only for packing. List of files to exclude seperated by ',' eg: "*.txt,*.png" or whole filenames
        :param info_file: additional files to add to the target zip files
        """

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
            image=f"{default_registry}/zip-unzip:3.0.0",
            name="zip-unzip",
            image_pull_secrets=["registry-secret"],
            env_vars=env_vars,
            execution_timeout=execution_timeout,
            **kwargs
        )
