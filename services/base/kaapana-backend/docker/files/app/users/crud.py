from sqlalchemy.orm import Session
from . import models, services, schemas
from fastapi import HTTPException, Depends
from app.dependencies import get_user_service


def create_project(db: Session, kaapana_project: schemas.KaapanaProject):
    db_project = models.Project(
        name=kaapana_project.name,
        group_id=kaapana_project.group_id,
        project_roles=kaapana_project.project_roles,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_project(db: Session, kaapana_project_name: str = ""):
    if kaapana_project_name:
        db_kaapana_project = (
            db.query(models.Project).filter_by(name=kaapana_project_name).first()
        )
        if not db_kaapana_project:
            raise HTTPException(status_code=404, detail="No project found!")
        db_kaapana_projects = [db_kaapana_project]
    else:
        db_kaapana_projects = db.query(models.Project).all()
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
