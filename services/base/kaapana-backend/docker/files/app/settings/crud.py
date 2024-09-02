import logging
from typing import Optional

# from app.config import settings
from app.workflows.crud import get_kaapana_instance, get_utc_timestamp
from sqlalchemy.orm import Session

from . import models, schemas

logging.getLogger().setLevel(logging.INFO)


def get_instance_settings(
    db: Session,
    instance_name: Optional[str] = None,
):
    db_kaapana_instance = get_kaapana_instance(db, instance_name)

    db_settings = (
        db.query(models.Settings)
        .filter_by(kaapana_instance_id=db_kaapana_instance.id)
        .all()
    )

    return db_settings


def get_settings_item(
    db: Session,
    settings_key: str,
    instance_name: Optional[str] = None,
):
    db_kaapana_instance = get_kaapana_instance(db, instance_name)

    db_settings_item = (
        db.query(models.Settings)
        .filter_by(kaapana_instance_id=db_kaapana_instance.id, key=settings_key)
        .one_or_none()
    )

    return db_settings_item


def create_or_update_settings(
    db: Session,
    settings_item: schemas.SettingsBase,
    instance_name: Optional[str] = None,
):
    db_kaapana_instance = get_kaapana_instance(db, instance_name)

    db_settings = get_settings_item(db, settings_item.key)

    if db_settings and (settings_item.value == db_settings.value):
        return db_settings

    if db_settings:
        db_settings.value = settings_item.value
        # update the current time
        db_settings.time_updated = get_utc_timestamp()

        db.commit()
        logging.debug(
            f"Successfully updated settings: {db_settings.key} for instance {db_kaapana_instance.instance_name}"
        )
        db.refresh(db_settings)
    else:
        # create new item
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
