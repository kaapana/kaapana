import logging
from app.dependencies import get_db
from app.workflows.crud import create_and_update_client_kaapana_instance
from app.workflows.schemas import ClientKaapanaInstanceCreate
from app.database import SessionLocal, engine

logging.getLogger().setLevel(logging.INFO)

with SessionLocal() as db:
    try:
        #get_remote_updates(db, periodically=True)
        client_kaapana_instance = ClientKaapanaInstanceCreate(**{
            "ssl_check": True,
            "automatic_update": False,
            "automatic_exp_execution": True,
            "fernet_encrypted": False,
            "allowed_dags": [],
            "allowed_datasets": []
        })
        create_and_update_client_kaapana_instance(db, client_kaapana_instance=client_kaapana_instance)
        logging.info('Client instance created!')
    except Exception as e:
        logging.warning('Client instance already created!')
        logging.warning(e)