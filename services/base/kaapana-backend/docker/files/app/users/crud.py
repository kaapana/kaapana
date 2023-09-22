from sqlalchemy.orm import Session
from sqlalchemy import select
from . import schemas
from app.workflows import models
from fastapi import HTTPException, Depends
from app.dependencies import get_user_service


def create_project(db: Session, kaapana_project: schemas.KaapanaProject):
    db_project = models.Project(
        name=kaapana_project.name,
        group_id=kaapana_project.group_id,
        project_roles=kaapana_project.project_roles,
        accesstable_primary_key=kaapana_project.accesstable_primary_key,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_project(db: Session, kaapana_project_name: str = ""):
    if kaapana_project_name:
        stmt = select(models.Project).filter(
            models.Project.name == kaapana_project_name
        )
        db_kaapana_project = db.execute(stmt).first()[0]
        if not db_kaapana_project:
            raise HTTPException(status_code=404, detail="No project found!")
        db_kaapana_projects = [db_kaapana_project]
    else:
        stmt = select(models.Project)
        db_kaapana_projects = db.execute(stmt)
        db_kaapana_projects = [r[0] for r in db_kaapana_projects]
    return db_kaapana_projects


def update_kaapana_project(db: Session, kaapana_project: schemas.KaapanaProject):
    db_project = models.Project(
        name=kaapana_project.name,
        group_id=kaapana_project.group_id,
        project_roles=kaapana_project.project_roles,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def delete_kaapana_project(db: Session, kaapana_project: schemas.KaapanaProject):
    db_kaapana_project = (
        db.query(models.Project).filter_by(name=kaapana_project.name).first()
    )
    if not db_kaapana_project:
        raise HTTPException(status_code=404, detail="Kaapana project not found")
    db.delete(db_kaapana_project)
    db.commit()
    return {"ok": True}


def create_access_table(db: Session, accesstable: schemas.AccessTable):
    """
    Create an accesstable
    """
    db_accesstable = models.AccessTable(
        object_primary_key=accesstable.object_primary_key
    )
    db.add(db_accesstable)
    db.commit()
    db.refresh(db_accesstable)
    return db_accesstable


def create_access_list_entree(
    db: Session, user: str, permissions: str, accesstable_primary_key
):
    """
    Create an access list entree
    """
    db_accesslistentree = models.AccessListEntree(
        user=user,
        permissions=permissions,
        accesstable_primary_key=accesstable_primary_key,
    )
    db.add(db_accesslistentree)
    db.commit()
    db.refresh(db_accesslistentree)
    return db_accesslistentree


def get_access_information(db: Session, model):
    """
    Get access information for all objects in the database.
    """
    stmt = (
        select(model, models.AccessListEntree)
        .join(
            models.AccessTable,
            models.AccessTable.object_primary_key == model.accesstable_primary_key,
        )
        .join(
            models.AccessListEntree,
            models.AccessListEntree.accesstable_primary_key
            == model.accesstable_primary_key,
        )
    )

    results = db.execute(stmt).all()
    data = {
        "Projects": [
            {"name": m.name, "user": acl.user, "permissions": acl.permissions}
            for m, acl in results
        ]
    }

    return data
