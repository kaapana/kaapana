import os
from fastapi import Header, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from minio import Minio
from .monitoring.services import MonitoringService
from .users.services import UserService

# from .workflows.services import WorkflowService
from .workflows.models import (
    KaapanaInstance,
    Project,
    Workflow,
    AccessListEntree,
)
from .config import settings
from .database import SessionLocal


def map_permission_to_sql_search(permission: str):
    if permission not in ("r", "w", "x"):
        raise ValueError("permission must be in (r,w,x)")
    return {"r": "r__", "w": "_w_", "x": "__x"}.get(permission)


def map_url_to_object(base_url, url: str):
    map = {
        base_url + "users/projects/": Project,
        base_url + "client/workflows": Workflow,
    }
    for key, value in map.items():
        if url.startswith(key):
            return value


def filter_query_by_user_and_permission(query, user, permission, model):
    permission = map_permission_to_sql_search(permission)
    filtered_query = (
        query.join(
            AccessListEntree,
            AccessListEntree.accessable_id == model.accessable_id,
        )
        .filter(AccessListEntree.user == user)
        .filter(AccessListEntree.permissions.like(permission))
    )
    return filtered_query


def my_get_db(request: Request):
    def my_decorator(func, db, user, requested_permission, requested_object):
        def filter_wrapper(statement, *args, **kwargs):
            db.num_executions = db.num_executions + 1
            print(f"Executed statements for this session: {db.num_executions}")
            if db.num_executions > 1:
                print("Execute original statement")
                return func(statement, *args, **kwargs)
            filtered_statement = filter_query_by_user_and_permission(
                statement, user, requested_permission, requested_object
            )
            return func(filtered_statement, *args, **kwargs)

        return filter_wrapper

    user = request.headers.get("x-forwarded-preferred-username", "")
    requested_permission = "r"
    base_url = request.base_url
    url = request.url
    requested_object = map_url_to_object(str(base_url), str(url))
    db = SessionLocal()
    db.num_executions = 0
    db.execute = my_decorator(
        db.execute,
        db,
        user=user,
        requested_permission=requested_permission,
        requested_object=requested_object,
    )
    try:
        yield db
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_monitoring_service() -> MonitoringService:
    yield MonitoringService(prometheus_url=settings.prometheus_url)


def get_user_service() -> UserService:
    yield UserService(
        settings.keycloak_url,
        settings.keycloak_admin_username,
        settings.keycloak_admin_password,
    )


def get_minio() -> Minio:
    yield Minio(
        settings.minio_url,
        access_key=settings.minio_username,
        secret_key=settings.minio_password,
        secure=False,
    )


# def get_workflow_service() -> WorkflowService:
#     yield WorkflowService(airflow_api=settings.airflow_url)


async def get_token_header(
    FederatedAuthorization: str = Header(...), db: Session = Depends(get_db)
):
    if FederatedAuthorization:
        db_client_kaapana_instance = (
            db.query(KaapanaInstance).filter_by(token=FederatedAuthorization).first()
        )
        if db_client_kaapana_instance:
            return db_client_kaapana_instance
        else:
            raise HTTPException(
                status_code=400, detail="FederatedAuthorization header invalid"
            )


async def get_query_token(token: str):
    if token != "jessica":
        raise HTTPException(status_code=400, detail="No Jessica token provided")
