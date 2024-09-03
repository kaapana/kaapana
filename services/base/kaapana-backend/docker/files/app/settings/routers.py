import logging
from re import sub
from typing import Any, List, Tuple, Union

import jsonschema.exceptions
from app.dependencies import get_db
from app.settings import crud, schemas
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

logging.getLogger().setLevel(logging.DEBUG)

router = APIRouter(tags=["settings"])


# get all settings for instance
@router.get("", response_model=List[schemas.SettingsBase])
def get_settings(db: Session = Depends(get_db)):
    db_response = crud.get_instance_settings(db)
    settings: List[schemas.SettingsBase] = []

    for item in db_response:
        settings_item = schemas.SettingsBase(key=item.key, value=item.value)
        settings.append(settings_item)

    return settings


# get workflow settings of a given dag for instance
@router.get("/workflows/{dag_id}", response_model=schemas.SettingsBase)
def get_workflow_settings(
    dag_id: str, snakecase: bool = False, db: Session = Depends(get_db)
):
    db_response = crud.get_settings_item(db, "workflows")

    settings_item: schemas.SettingsBase = schemas.SettingsBase(key=dag_id, value={})
    if db_response:
        workflows = db_response.value
        dag_id_converted = camel_case(dag_id)
        if dag_id_converted in workflows:
            workflow_settings = workflows[dag_id_converted]
            if snakecase:
                workflow_settings = convert_dict_keys_to_snake_case(workflow_settings)
            settings_item = schemas.SettingsBase(key=dag_id, value=workflow_settings)

    return settings_item


# put all settings for instance
@router.put("")
def create_or_update_settings(
    settings: List[schemas.SettingsBase], db: Session = Depends(get_db)
):
    for item in settings:
        _ = crud.create_or_update_settings(db, item)
    return True


@router.put("/item")
def create_or_update_settings_item(
    settings_item: schemas.SettingsBase, db: Session = Depends(get_db)
):
    updated_item = crud.create_or_update_settings(db, settings_item)
    settings_item.value = updated_item.value

    return settings_item


def convert_dict_keys_to_snake_case(target_dict):
    new_dict = {}
    for key in target_dict.keys():
        new_key = snake_case(key)
        if isinstance(target_dict[key], dict):
            new_dict[new_key] = convert_dict_keys_to_snake_case(target_dict[key])
        else:
            new_dict[new_key] = target_dict[key]
    return new_dict


# Define a function to convert a string to camel case
def camel_case(s):
    # Use regular expression substitution to replace underscores and hyphens with spaces,
    # then title case the string (capitalize the first letter of each word), and remove spaces
    s = sub(r"(_|-)+", " ", s).title().replace(" ", "")

    # Join the string, ensuring the first letter is lowercase
    return "".join([s[0].lower(), s[1:]])


def snake_case(name):
    name = sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()
