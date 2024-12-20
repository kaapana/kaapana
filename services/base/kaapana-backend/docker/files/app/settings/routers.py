import logging
from typing import List

from app.dependencies import get_db
from app.settings import crud, schemas
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

logging.getLogger().setLevel(logging.DEBUG)

router = APIRouter(tags=["settings"])


# get all settings for instance
@router.get("", response_model=List[schemas.SettingsBase])
def get_settings(
    db: Session = Depends(get_db),
    preferred_username=Header(..., alias="X-Forwarded-Preferred-Username"),
):
    db_response = crud.get_instance_settings(db, username=preferred_username)
    settings: List[schemas.SettingsBase] = []

    for item in db_response:
        settings_item = schemas.SettingsBase(key=item.key, value=item.value)
        settings.append(settings_item)

    return settings


# get workflow settings of a given dag for instance
@router.get("/workflows/{dag_id}", response_model=schemas.SettingsBase)
def get_workflow_settings(
    dag_id: str,
    db: Session = Depends(get_db),
    preferred_username=Header(..., alias="X-Forwarded-Preferred-Username"),
):
    db_response = crud.get_settings_item(db, "workflows")
    if preferred_username != "system":
        db_response = crud.get_settings_item(
            db, "workflows", username=preferred_username
        )

    settings_item: schemas.SettingsBase = schemas.SettingsBase(key=dag_id, value={})
    if db_response:
        workflows = db_response.value
        # dag_id_converted = camel_case(dag_id)
        if dag_id in workflows:
            workflow_settings = workflows[dag_id]
            settings_item = schemas.SettingsBase(key=dag_id, value=workflow_settings)

    return settings_item


# put all settings for instance
@router.put("")
def create_or_update_settings(
    settings: List[schemas.SettingsBase],
    db: Session = Depends(get_db),
    preferred_username=Header(..., alias="X-Forwarded-Preferred-Username"),
):
    for item in settings:
        _ = crud.create_or_update_settings(db, item, username=preferred_username)
    return True


@router.put("/item")
def create_or_update_settings_item(
    settings_item: schemas.SettingsBase,
    db: Session = Depends(get_db),
    preferred_username=Header(..., alias="X-Forwarded-Preferred-Username"),
):
    updated_item = crud.create_or_update_settings(
        db, settings_item, username=preferred_username
    )
    settings_item.value = updated_item.value

    return settings_item
