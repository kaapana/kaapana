import datetime
import glob
import json
import os
from datetime import timedelta
from zipfile import ZipFile

import requests
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.HelperMinio import HelperMinio
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.logger import get_logger
from minio import Minio

logger = get_logger(__name__)


class LocalMinioOperator(KaapanaPythonBaseOperator):
    """
    Operator to communicate with MinIO buckets
    """

    def get_project_by_name(self, project_name: str):
        response = requests.get(
            f"http://aii-service.{SERVICES_NAMESPACE}.svc:8080/projects/{project_name}",
            params={"name": project_name},
        )
        response.raise_for_status()
        project = response.json()
        return project

    def get_project_bucket_from_meta_json(self, json_dict):
        logger.info(f"Applying action to project bucket")
        id = json_dict["0020000E SeriesInstanceUID_keyword"]
        clinical_trial_protocol_id = json_dict.get(
            "00120020 ClinicalTrialProtocolID_keyword"
        )[0]

        project = self.get_project_by_name(clinical_trial_protocol_id)

        if project:
            return project["s3_bucket"]
        else:
            return None

    def get_project_bucket_from_json(self, batch_folders):
        for batch_element_dir in batch_folders:
            json_dir = os.path.join(
                batch_element_dir, self.json_operator.operator_out_dir
            )
            json_list = glob.glob(json_dir + "/**/*.json", recursive=True)
            logger.info(f"Found json files: {json_list}")
            assert len(json_list) > 0

            with open(json_list[0], encoding="utf-8") as f:
                new_json = json.load(f)

            return self.get_project_bucket_from_meta_json(new_json)

    @cache_operator_output
    def start(self, ds, **kwargs):
        dag_run = kwargs["dag_run"]
        conf = kwargs["dag_run"].conf
        print("conf", conf)
        if (
            conf is not None
            and "form_data" in conf
            and conf["form_data"] is not None
            and "zip_files" in conf["form_data"]
        ):
            self.zip_files = conf["form_data"]["zip_files"]
            print("Zip files set by form data", self.zip_files)

        if conf is not None and "data_form" in conf:
            for attr in [
                "bucket_name",
                "action_operator_dirs",
                "action_operators",
                "action_files",
            ]:
                if attr in conf["data_form"]:
                    print(f'From data_form {attr}={conf["data_form"][attr]}')
                    setattr(self, attr, conf["data_form"][attr])
        ###################
        # TODO: Can't be used like this, since token expires, we should use presigned_urls, which should be generated when the airflow is triggered
        # if 'conf' in conf:
        #     if 'x_auth_token' in conf:
        #         access_key, secret_key, session_token = generate_minio_credentials(conf['x_auth_token'])
        #     else:
        #         access_key = os.environ.get('MINIOUSER'),
        #         secret_key = os.environ.get('MINIOPASSWORD')
        #         session_token = None
        ###################

        # Todo: actually should be in pre_execute, however, when utilizing
        # Airflow PythonOperator pre_execute seems to have no effect...
        # For files coming from Minio hooks!
        if conf is not None and "Key" in conf:
            self.bucket_name = conf["Key"].split("/")[0]
            object_names = ["/".join(conf["Key"].split("/")[1:])]
        else:
            object_names = []

        minioClient = HelperMinio(dag_run=dag_run)

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        local_root_dir = self.local_root_dir.format(run_dir=run_dir)

        print(f"Working relative to the following director: {local_root_dir}")
        batch_folder = [
            f for f in glob.glob(os.path.join(local_root_dir, self.batch_name, "*"))
        ]

        print(batch_folder)
        if self.json_operator:
            project_bucket = self.get_project_bucket_from_json(batch_folder)
            self.bucket_name = project_bucket

        if self.bucket_name is None:
            print("No BUCKETID env set!")
            self.bucket_name = kwargs["dag"].dag_id
            print("Generated Bucket-Id: %s" % self.bucket_name)

        object_dirs = []
        # Get contents from run_dir
        object_dirs = object_dirs + self.action_operator_dirs
        for action_operator in self.action_operators:
            object_dirs.append(
                os.path.relpath(
                    os.path.join(run_dir, action_operator.operator_out_dir),
                    local_root_dir,
                )
            )

        # Get contents from batch_elements
        for batch_element_dir in batch_folder:
            for operator_dir in self.action_operator_dirs:
                object_dirs.append(
                    os.path.relpath(
                        os.path.join(batch_element_dir, operator_dir), local_root_dir
                    )
                )
            for action_operator in self.action_operators:
                object_dirs.append(
                    os.path.relpath(
                        os.path.join(
                            batch_element_dir, action_operator.operator_out_dir
                        ),
                        local_root_dir,
                    )
                )

        # Files to apply action
        # Add object_names
        object_names = object_names + self.action_files
        # Add relative file paths from operators
        for object_dir in object_dirs:
            for action_file in self.action_files:
                object_names.append(os.path.join(object_dir, action_file))

        if self.zip_files:
            timestamp = (datetime.datetime.now()).strftime("%y-%m-%d-%H:%M:%S%f")
            target_dir = os.path.join(run_dir, self.operator_out_dir)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            zip_object_name = (
                f"{kwargs['dag'].dag_id}_{kwargs['dag_run'].run_id}_{timestamp}.zip"
            )
            zip_file_path = os.path.join(target_dir, zip_object_name)
            with ZipFile(zip_file_path, "w") as zipObj:
                if not object_dirs:
                    print(f"Zipping everything from {local_root_dir}")
                    object_dirs = [""]
                else:
                    print(f'Zipping everything from {", ".join(object_dirs)}')
                for object_dir in object_dirs:
                    for path, _, files in os.walk(
                        os.path.join(local_root_dir, object_dir)
                    ):
                        for name in files:
                            file_path = os.path.join(path, name)
                            rel_dir = os.path.relpath(path, local_root_dir)
                            rel_dir = "" if rel_dir == "." else rel_dir
                            if rel_dir == self.operator_out_dir:
                                print(
                                    "Skipping files in {rel_dir}, due to "
                                    "recursive zipping!"
                                )
                                continue
                            object_name = os.path.join(rel_dir, name)
                            zipObj.write(os.path.join(path, name), object_name)

            # append directory prefix before zip object name
            # to store the zip file inside target directory of the bucket
            if self.target_dir_prefix and self.target_dir_prefix != "":
                zip_object_name = os.path.join(self.target_dir_prefix, zip_object_name)

            minioClient.apply_action_to_file(
                "put",
                self.bucket_name,
                zip_object_name,
                zip_file_path,
                self.file_white_tuples,
            )
            return

        if object_names:
            print(f'Applying action "{self.action}" to files {object_names}')
            minioClient.apply_action_to_object_names(
                self.action,
                self.bucket_name,
                local_root_dir,
                object_names,
                self.file_white_tuples,
                target_dir_prefix=self.target_dir_prefix,
            )
        else:
            if not object_dirs:
                print(f"Applying action to whole bucket")
            else:
                print(f'Applying action "{self.action}" to ' f"files in: {object_dirs}")

            minioClient.apply_action_to_object_dirs(
                self.action,
                self.bucket_name,
                local_root_dir,
                object_dirs,
                self.file_white_tuples,
                target_dir_prefix=self.target_dir_prefix,
            )

        return

    def __init__(
        self,
        dag,
        action="get",  # 'get', 'remove' or 'put'
        name=None,
        local_root_dir="{run_dir}",
        bucket_name=None,
        action_operators=None,
        action_operator_dirs=None,
        action_files=None,
        json_operator=None,
        minio_host: str = f"minio-service.{SERVICES_NAMESPACE}.svc",
        minio_port: str = "9000",
        file_white_tuples=None,
        zip_files: bool = False,
        target_dir_prefix: str = "",
        **kwargs,
    ):
        """
        :param action: Action to execute ('get', 'remove' or 'put')
        :param local_root_dir: Workflow directory
        :param bucket_name: Name of the Bucket to interact with
        :param action_operators: Operator to use the output data from
        :param action_operator_dirs: (Additional) directory to apply MinIO
            action on.
        :param action_files: (Additional) files to apply MinIO action on.
        :param json_operator: (Additional) Operator that convert dicom to JSON. Json data used to extract project name from metadata.
        :param minio_host: MinIO host
        :param minio_port: MinIO port
        :param file_white_tuples: Optional whitelisting for files
        :param zip_files: If files should be zipped
        :param target_dir_prefix: Specifies if files will be copied inside a target directory within the bucket. Applicable
            only for the `put` action.
        """

        if action not in ["get", "remove", "put"]:
            raise AssertionError("action must be get, remove or put")

        if action == "put":
            file_white_tuples = file_white_tuples or (
                ".json",
                ".mat",
                ".py",
                ".zip",
                ".txt",
                ".gz",
                ".csv",
                "pdf",
                "png",
                "jpg",
            )
        name = name or f"minio-actions-{action}"
        self.action = action
        self.local_root_dir = local_root_dir
        self.bucket_name = bucket_name
        self.action_operator_dirs = action_operator_dirs or []
        self.action_operators = action_operators or []
        self.action_files = action_files or []
        self.json_operator = json_operator
        self.minio_host = minio_host
        self.minio_port = minio_port
        self.file_white_tuples = file_white_tuples
        self.zip_files = zip_files
        self.target_dir_prefix = target_dir_prefix

        super(LocalMinioOperator, self).__init__(
            dag=dag,
            name=name,
            python_callable=self.start,
            execution_timeout=timedelta(minutes=30),
            **kwargs,
        )
