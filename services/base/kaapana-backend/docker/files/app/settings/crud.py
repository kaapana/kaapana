import json
import logging
from typing import Optional

from app.workflows import models

# from app.config import settings
from app.workflows.crud import get_kaapana_instance, get_utc_timestamp
from sqlalchemy.orm import Session

from . import schemas

logging.getLogger().setLevel(logging.INFO)


list_idntifier = "::list::"
list_seperator = "|| ||"


def process_incoming_value(value):
    """
    Process the incoming value before storing it in the database.

    - If the value is a dictionary, it is converted to a JSON string.
    - If the value is a list, it is converted to a string by joining elements with a separator and adding a list identifier.
    - For any other data type, the value is returned as is.

    Args:
        value (Any): The incoming value to be processed, which can be of any data type.

    Returns:
        Any: The processed value, either as a string (for dicts and lists) or in its original form.
    """
    if isinstance(value, dict):
        return json.dumps(value)
    elif isinstance(value, list):
        return f"{list_seperator.join(value)}{list_idntifier}"
    return value


def process_result_value(value):
    """
    Process the stored value after retrieving it from the database.

    - If the value is a JSON string, it is converted back to a dictionary.
    - If the value is a string ending with a list identifier, it is split into a list using the separator.
    - If the value is neither a valid JSON nor a list, it is returned as is.

    Args:
        value (str): The value to be processed, typically retrieved from the database.

    Returns:
        Any: The processed value, which could be a dictionary, list, or the original value.
    """
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        if isinstance(value, str) and value.endswith(list_idntifier):
            temp = value.replace(list_idntifier, "")
            value = temp.split(list_seperator)
        return value


def get_instance_settings(
    db: Session,
    instance_name: Optional[str] = None,
):
    """
    Retrieve all settings for a given instance from the database.

    Args:
        db (Session): The database session to be used for the query.
        instance_name (Optional[str]): The name of the instance for which settings should be retrieved.

    Returns:
        List[models.Settings]: A list of all settings for the specified instance with processed values.
    """
    # Retrieves the `kaapana_instance` by its name or the default instance if none is specified.
    db_kaapana_instance = get_kaapana_instance(db, instance_name)

    # Queries all settings related to the `kaapana_instance`.
    db_settings = (
        db.query(models.Settings)
        .filter_by(kaapana_instance_id=db_kaapana_instance.id)
        .all()
    )

    # Processes the value of each setting before returning it.
    for item in db_settings:
        item.value = process_result_value(item.value)

    return db_settings


def get_settings_item(
    db: Session,
    settings_key: str,
    instance_name: Optional[str] = None,
):
    """
    Retrieve a specific setting item for a given instance from the database.

    Args:
        db (Session): The database session to be used for the query.
        settings_key (str): The key of the setting to be retrieved.
        instance_name (Optional[str]): The name of the instance for which the setting should be retrieved.

    Returns:
        models.Settings: The setting item corresponding to the given key and instance, with a processed value.
    """
    # Retrieves the `kaapana_instance` by its name or the default instance if none is specified.
    db_kaapana_instance = get_kaapana_instance(db, instance_name)

    # Queries the specific setting by key for the `kaapana_instance`.
    db_settings_item = (
        db.query(models.Settings)
        .filter_by(kaapana_instance_id=db_kaapana_instance.id, key=settings_key)
        .one_or_none()
    )

    # Processes the value of the setting before returning it.
    db_settings_item.value = process_result_value(db_settings_item.value)

    return db_settings_item


def create_or_update_settings(
    db: Session,
    settings_item: schemas.SettingsBase,
    instance_name: Optional[str] = None,
):
    """
    Create or update a settings item in the database for a given instance.

    Args:
        db (Session): The database session to be used for the operation.
        settings_item (schemas.SettingsBase): The settings item to be created or updated.
        instance_name (Optional[str]): The name of the instance for which the setting should be created or updated.

    Returns:
        models.Settings: The created or updated settings item.
    """
    # Processes the incoming value before storing it.
    settings_item.value = process_incoming_value(settings_item.value)

    # Retrieves the existing setting by key for the `kaapana_instance`.
    db_kaapana_instance = get_kaapana_instance(db, instance_name)
    db_settings = get_settings_item(db, settings_item.key)

    # If the setting exists and the value is unchanged, the existing setting is returned.
    if db_settings and (settings_item.value == db_settings.value):
        return db_settings

    if db_settings:
        # If the setting exists and the value has changed, it is updated and the timestamp is refreshed.
        db_settings.value = settings_item.value
        # update the current time
        db_settings.time_updated = get_utc_timestamp()

        db.commit()
        logging.debug(
            f"Successfully updated settings: {db_settings.key} for instance {db_kaapana_instance.instance_name}"
        )
        db.refresh(db_settings)
    else:
        # If the setting does not exist, a new one is created.
        db_settings = models.Settings(
            username="",
            instance_name=db_kaapana_instance.instance_name,
            key=settings_item.key,
            value=settings_item.value,
            time_created=get_utc_timestamp(),
            time_updated=get_utc_timestamp(),
            kaapana_instance_id=db_kaapana_instance.id,
        )

        db.add(db_settings)
        db.commit()
        logging.debug(
            f"Successfully created dataset: {db_settings.key} for instance {db_kaapana_instance.instance_name}"
        )

        db.refresh(db_settings)

    return db_settings
