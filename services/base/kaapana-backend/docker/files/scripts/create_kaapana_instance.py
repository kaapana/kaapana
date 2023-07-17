import logging
from app.dependencies import get_db
from app.workflows.crud import (
    create_and_update_client_kaapana_instance,
    get_kaapana_instances,
)
from app.workflows.schemas import ClientKaapanaInstanceCreate
from app.database import SessionLocal, engine
from app.config import settings

logging.getLogger().setLevel(logging.INFO)

with SessionLocal() as db:
    try:
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
            db_client_kaapana_instance = create_and_update_client_kaapana_instance(
                db, client_kaapana_instance=client_kaapana_instance
            )
            logging.info("Client instance created!")
        for db_kaapana_instance in db_kaapana_instances:
            if not db_kaapana_instance.remote:
                if db_kaapana_instance.instance_name != settings.instance_name:
                    db_kaapana_instance.instance_name = settings.instance_name
                    db.add(db_kaapana_instance)
                    db.commit()
                    db.refresh(db_kaapana_instance)
                    logging.info("Client instance updated!")
                else:
                    logging.info("Client instance needs no update!")
                break
    except Exception as e:
        logging.warning("Client instance already created!")
        logging.warning(e)
