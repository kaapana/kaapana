import httpx
from app.config import settings
from app.database import SessionLocal
from app.workflows.crud import (
    create_and_update_client_kaapana_instance,
    get_kaapana_instances,
)
from app.workflows.schemas import ClientKaapanaInstanceCreate
from kaapanapy.logger import get_logger
from tenacity import (
    retry,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_fixed,
)

logger = get_logger(__name__)


@retry(
    stop=stop_after_attempt(10),  # Retry up to 10 times
    wait=wait_fixed(30),  # Wait 2 seconds between retries
    retry=(
        retry_if_exception_type(httpx.HTTPError) | retry_if_result(lambda r: r is None)
    ),
)
def fetch_project_id():
    try:
        response = httpx.get(
            "http://aii-service.services.svc:8080/projects/admin", timeout=5
        )
        response.raise_for_status()
        project = response.json()
        project_id = project.get("id")

        if project_id:
            logger.info(f"Fetched project UUID: {project_id}")
            return project_id
        else:
            logger.warning("Project UUID missing in response.")

    except httpx.HTTPError as e:
        logger.warning(f"HTTP error while fetching project UUID: {e}")
        raise  # Will trigger a retry

    return None  # Will trigger a retry if UUID wasn't found


def main():
    with SessionLocal() as db:
        db_kaapana_instances = get_kaapana_instances(db)
        if not db_kaapana_instances:
            client_kaapana_instance = ClientKaapanaInstanceCreate(
                **{
                    "ssl_check": False,
                    "automatic_update": False,
                    "automatic_workflow_execution": True,
                    "fernet_encrypted": False,
                }
            )
            project_id = fetch_project_id()
            logger.info(f"Project UUID: {project_id}")

            create_and_update_client_kaapana_instance(
                db,
                client_kaapana_instance=client_kaapana_instance,
                project_id=project_id,
            )
            logger.info("Client instance created!")

        for db_kaapana_instance in db_kaapana_instances:
            if not db_kaapana_instance.remote:
                if db_kaapana_instance.instance_name != settings.instance_name:
                    db_kaapana_instance.instance_name = settings.instance_name
                    db.add(db_kaapana_instance)
                    db.commit()
                    db.refresh(db_kaapana_instance)
                    logger.info("Client instance updated!")
                else:
                    logger.info("Client instance needs no update!")
                break


if __name__ == "__main__":
    main()
