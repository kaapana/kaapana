import os
from pathlib import Path

import pydicom
from kaapanapy.helper import load_workflow_config
from kaapanapy.logger import get_logger
from kaapanapy.services.NotificationService import (
    NotificationCreate,
    NotificationService,
)
from kaapanapy.settings import OperatorSettings
from kaapanapy.utils import (
    ConfigError,
    get_keycloak_id,
    process_batches,
    process_single,
)

logger = get_logger(__name__)


def main():
    try:
        config = load_workflow_config()

        username = config["workflow_form"]["username"]
        project_name = config["project_form"]["name"]

        # Airflow variables
        operator_settings = OperatorSettings()
        thread_count = int(os.getenv("THREADS", "3"))
        if thread_count is None:
            logger.error("Missing required environment variable: THREADS")
            raise ConfigError("Missing required environment variable: THREADS")

        # Operator settings variables
        run_id = operator_settings.run_id
        dag_id = operator_settings.dag_id
        task_id = operator_settings.task_id
        workflow_dir = Path(operator_settings.workflow_dir)
        batch_name = operator_settings.batch_name
        operator_in_dir = Path(operator_settings.operator_in_dir)
        operator_out_dir = Path(operator_settings.operator_out_dir)

        if not workflow_dir.exists():
            logger.error(f"{workflow_dir} directory does not exist")
            raise ConfigError(f"{workflow_dir} directory does not exist")

        batch_dir = workflow_dir / batch_name
        if not batch_dir.exists():
            logger.error(f"{batch_dir} directory does not exist")
            raise ConfigError(f"{batch_dir} directory does not exist")
    except Exception as e:
        logger.critical(f"Configuration error: {e}")
        raise SystemExit(1)  # Gracefully exit the program

    def process(
        operator_in_dir: Path,
        operator_out_dir: Path,
    ):
        logger.info(f"operator_in_dir: {operator_in_dir}")
        logger.info(f"operator_out_dir: {operator_out_dir}")
        dicom_files = [
            pydicom.dcmread(filename) for filename in operator_in_dir.iterdir()
        ]
        # Do whatever you need with the DCMs files
        notification = NotificationCreate(
            topic="Debug",
            title="Otsus Operator successful",
            description=f"{len(dicom_files)} dicom files found and processed! Operator was successful",
            icon="mdi-information",
            link=f"/flow/dags/{dag_id}/grid?root=&dag_run_id={run_id}&task_id={task_id}&tab=logs",
        )
        NotificationService.post_notification_to_user(
            user_id=get_keycloak_id(username),
            project_id=project_name,
            notification=notification,
        )
        return True, operator_in_dir

    if not config["workflow_form"]["single_execution"]:
        process_batches(
            # Required
            batch_dir=Path(batch_dir),
            operator_in_dir=Path(operator_in_dir),
            operator_out_dir=Path(operator_out_dir),
            processing_function=process,
            thread_count=thread_count,
        )
    else:
        process_single(
            # Required
            base_dir=Path(os.environ["WORKFLOW_DIR"]),
            operator_in_dir=Path(operator_in_dir),
            operator_out_dir=Path(operator_out_dir),
            processing_function=process,
            thread_count=thread_count,
        )


if __name__ == "__main__":
    main()
