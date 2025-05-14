from pathlib import Path
from typing import Optional

from kaapanapy.helper import load_workflow_config
from kaapanapy.logger import get_logger
from kaapanapy.services.NotificationService import Notification, NotificationService
from kaapanapy.settings import OperatorSettings
from kaapanapy.utils import ConfigError, get_user_id
from pydantic_settings import BaseSettings

logger = get_logger(__name__)


class NotificationOperatorSettings(BaseSettings):
    topic: Optional[str] = None
    title: str
    description: str
    icon: Optional[str] = None
    link: Optional[str] = None


def main():
    try:
        config = load_workflow_config()

        username = config["workflow_form"]["username"]
        project_name = config["project_form"]["name"]

        # Airflow variables
        operator_settings = OperatorSettings()

        run_id = operator_settings.run_id
        dag_id = operator_settings.dag_id
        task_id = operator_settings.task_id
        workflow_dir = Path(operator_settings.workflow_dir)
        batch_name = operator_settings.batch_name

        if not workflow_dir.exists():
            logger.error(f"{workflow_dir} directory does not exist")
            raise ConfigError(f"{workflow_dir} directory does not exist")

        batch_dir = workflow_dir / batch_name
        if not batch_dir.exists():
            logger.error(f"{batch_dir} directory does not exist")
            raise ConfigError(f"{batch_dir} directory does not exist")

        notification_settings = NotificationOperatorSettings()
    except Exception as e:
        logger.critical(f"Configuration error: {e}")
        raise SystemExit(1)  # Gracefully exit the program

    notification = Notification(
        topic=notification_settings.topic if notification_settings.topic else dag_id,
        title=notification_settings.title,
        description=notification_settings.description,
        icon=(
            notification_settings.icon
            if notification_settings.icon
            else "mdi-information"
        ),
        link=(
            notification_settings.link
            if notification_settings.link
            else f"/flow/dags/{dag_id}/grid?root=&dag_run_id={run_id}&task_id={task_id}&tab=logs"
        ),
    )
    NotificationService.send(
        user_ids=[get_user_id(username)],
        project_id=project_name,
        notification=notification,
    )


if __name__ == "__main__":
    main()
