from sqlalchemy.orm import Session
from . import models, services, schemas
from fastapi import HTTPException, Depends
from app.dependencies import get_user_service


def create_project(db: Session, kaapana_project: schemas.KaapanaProject):
    db_project = models.Project(
        name=kaapana_project.name,
        group_idx=kaapana_project.group_idx,
        role_admin_idx=kaapana_project.role_admin_idx,
        role_member_idx=kaapana_project.role_member_idx,
    )

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return db_project


def get_project(db: Session, kaapana_project_name: str = ""):
    print(models.Project.__table__)
    print(dir(models.Project))
    if kaapana_project_name:
        db_kaapana_project = (
            db.query(models.Project).filter_by(name=kaapana_project_name).first()
        )
        if not db_kaapana_project:
            raise HTTPException(status_code=404, detail="No project found!")
        db_kaapana_projects = [db_kaapana_project]
    else:
        db_kaapana_projects = db.query(models.Project).all()
    if not db_kaapana_projects:
        raise HTTPException(status_code=404, detail="No project found!")

    return db_kaapana_projects


def update_kaapana_project(db: Session, kaapana_project: schemas.KaapanaProject):
    db_project = models.Project(
        name=kaapana_project.name,
        group_idx=kaapana_project.group_idx,
        role_admin_idx=kaapana_project.role_admin_idx,
        role_member_idx=kaapana_project.role_member_idx,
    )

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return db_project


def delete_kaapana_project(db: Session, kaapana_project_id: int):
    db_kaapana_project = (
        db.query(models.Project).filter_by(id=kaapana_project_id).first()
    )
    if not db_kaapana_project:
        raise HTTPException(status_code=404, detail="Kaapana project not found")
    db.delete(db_kaapana_project)
    db.commit()
    return {"ok": True}
