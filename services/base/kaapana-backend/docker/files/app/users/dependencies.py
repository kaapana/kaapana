from fastapi import Depends, Request, BackgroundTasks
from app.dependencies import get_db

from .crud import create_access_list_entree, create_access_table, get_access_information
import string, random
from app.workflows.models import AccessTable, Project
import requests


def create_access_table_and_list(request: Request, db=Depends(get_db)):
    characters = string.ascii_uppercase + string.ascii_lowercase + string.digits
    access_table_primary = "".join(random.choices(characters, k=6))
    access_table = AccessTable(
        object_primary_key=access_table_primary,
    )
    access_table = create_access_table(db=db, accesstable=access_table)
    ### Create permissions for creator
    if "x-forwarded-preferred-username" in request.headers:
        user = request.headers["x-forwarded-preferred-username"]
    else:
        AssertionError
    create_access_list_entree(
        db=db,
        user=user,
        permissions="rwx",
        accesstable_primary_key=access_table_primary,
    )
    return access_table_primary


def put_opa_data(data, path):
    print(f"Put data to opa at {path=}")
    url = f"http://open-policy-agent-service.services.svc:8181/v1/data/{path}"
    r = requests.put(url, json=data)


def get_opa_data(package="httpapi/authz"):
    print(f"Get data from OPA at {package=}")
    r = requests.get(
        f"http://open-policy-agent-service.services.svc:8181/v1/data/{package}"
    )
    return r.json()


def opa_background_task(db, model, target):
    data = get_access_information(db, model)
    put_opa_data(data, target)


def fetch_data_and_put_to_opa(
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
):
    background_tasks.add_task(opa_background_task, db, Project, "project/example")
