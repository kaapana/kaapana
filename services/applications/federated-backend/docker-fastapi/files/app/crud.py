import json
import uuid

from sqlalchemy.orm import Session
from cryptography.fernet import Fernet


from . import models, schemas
from app.utils import json_loads_client_network
from urllib.parse import urlparse

def get_client_network(db: Session):
    db_client_network = db.query(models.ClientNetwork).first()
    return json_loads_client_network(db_client_network)


def create_client_network(db: Session, client_network: schemas.ClientNetworkCreate, request):

    db.query(models.ClientNetwork).delete()
    db.commit()

    if client_network.fernet_encrypted is True:
        fernet_key=Fernet.generate_key().decode()
    else:
        fernet_key='deactivated'

    url = urlparse(str(request.url))
    db_client_network = models.ClientNetwork(
        token=str(uuid.uuid4()),
        protocol='https',
        host=url.hostname,
        port=url.port or 443,
        ssl_check=client_network.ssl_check,
        fernet_key=fernet_key,
        allowed_dags=json.dumps(client_network.allowed_dags),
        allowed_datasets=json.dumps(client_network.allowed_datasets),
        automatic_update=client_network.automatic_update or False,
        automatic_job_execution=client_network.automatic_job_execution or False
    )

    db.add(db_client_network)
    db.commit()
    db.refresh(db_client_network)
    return json_loads_client_network(db_client_network)


def get_remote_network(db: Session):
    return db.query(models.RemoteNetwork).first()


def create_remote_network(db: Session, remote_network: schemas.RemoteNetworkCreate):

    db.query(models.RemoteNetwork).delete()
    db.commit()
    db_remote_network = models.RemoteNetwork(
            token=remote_network.token,
            protocol='https',
            host=remote_network.host,
            port=remote_network.port,
            ssl_check=remote_network.ssl_check,
            fernet_key=remote_network.fernet_key or 'deactivated',
        )

    db.add(db_remote_network)
    db.commit()
    db.refresh(db_remote_network)
    return db_remote_network