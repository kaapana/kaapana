import os
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from minio import Minio
from .monitoring.services import MonitoringService
from .users.services import UserService

# from .workflows.services import WorkflowService
from .workflows.models import KaapanaInstance
from .config import settings
from .database import SessionLocal
from .users.models import Project, AccessTable, AccessListEntree


def map_permission_to_sql_search(permission: str):
    if permission not in ("r", "w", "x"):
        raise ValueError("permission must be in (r,w,x)")
    return {"r": "r__", "w": "_w_", "x": "__x"}.get(permission)


def filter_to_sqlalchemy(filter_key: str):
    """
    Return the object corresponding to the filter key
    """
    filter_key
    table, column = filter_key.split(".")
    Str2Object = {
        "Project": {
            "name": Project.name,
            "group_id": Project.group_id,
            "project_roles": Project.project_roles,
            "accesstable_primary_key": Project.accesstable_primary_key,
        },
        "AccessTable": AccessTable,
        "AccessListEntree": AccessListEntree,
    }
    filter_target = Str2Object.get(table).get(column)
    return filter_target


def filter_query_by_user_and_permission(query, user, permission, model):
    permission = map_permission_to_sql_search(permission)
    filtered_query = (
        query.join(
            AccessTable,
            AccessTable.object_primary_key == model.accesstable_primary_key,
        )
        .join(
            AccessListEntree,
            AccessListEntree.accesstable_primary_key == model.accesstable_primary_key,
        )
        .filter(AccessListEntree.user == user)
        .filter(AccessListEntree.permissions.like(permission))
    )
    return filtered_query


class KaapanaDB:
    """
    Custom context manager that is supposed to work with fastapi dependencies
    """

    def __init__(self, kaapana_filter):
        self.db = SessionLocal()
        print("Am I even initialized?!?")
        self.kaapana_filter = kaapana_filter

        def my_decorator(func):
            def wrapper(statement, kaapana_filter=self.kaapana_filter, **kwargs):
                print(f"{kaapana_filter=}")
                print("Decorator in use!!!")
                filter_key, filter_val = kaapana_filter
                if filter_key and filter_val:
                    filter_row_object = filter_to_sqlalchemy(filter_key)
                    filtered_statement = statement.filter(
                        filter_row_object == filter_val
                    )

                    print(filtered_statement)
                else:
                    # filtered_statement = statement
                    filtered_statement = filter_query_by_user_and_permission(
                        statement, "kaapana", "r", Project
                    )
                return func(filtered_statement, *kwargs)

            return wrapper

        print("Set decorator for execute function")
        self.db.execute = my_decorator(self.db.execute)

    # def __enter__(self):
    #     print("Is this method even called?!?!")

    #     def my_decorator(func):
    #         def wrapper(statement, kaapana_filter=self.kaapana_filter, **kwargs):
    #             print(f"{kaapana_filter=}")
    #             print("Decorator in use!!!")
    #             func(statement, *kwargs)

    #         return wrapper

    #     print("Set decorator for execute function")
    #     self.db.execute = my_decorator(self.db.execute)
    #     return self.db

    # def __exit__(self, exc_type, exc_value, traceback):
    #     self.db.close()

    def close(self):
        self.db.close()


def my_get_db(filter_key: str = "", filter_value: str = ""):
    db = KaapanaDB((filter_key, filter_value))
    print("Do I use this!?!?!")
    try:
        yield db.db
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
