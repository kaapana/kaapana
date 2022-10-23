
from app.dependencies import get_db
from app.experiments.crud import create_and_update_client_kaapana_instance
from app.experiments.schemas import ClientKaapanaInstanceCreate
from app.database import SessionLocal, engine


with SessionLocal() as db:
    try:
        #get_remote_updates(db, periodically=True)
        client_kaapana_instance = ClientKaapanaInstanceCreate(**{
            "ssl_check": True,
            "automatic_update": False,
            "automatic_job_execution": True,
            "fernet_encrypted": False,
            "allowed_dags": [],
            "allowed_datasets": []
        })
        create_and_update_client_kaapana_instance(db, client_kaapana_instance=client_kaapana_instance)
        print('Client instance created!')
    except Exception as e:
        print('Client instance already created!')
        print(e)