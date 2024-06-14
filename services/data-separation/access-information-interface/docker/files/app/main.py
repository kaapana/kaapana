from fastapi import FastAPI
from .aii.routes import router as aii_router
from .projects.routes import router as projects_router
from .projects.crud import (
    create_rights,
    create_roles,
    create_roles_rights_mapping,
    get_roles,
    get_rights,
    create_project,
    create_users_projects_roles_mapping,
    get_projects,
)
from .projects.schemas import CreateRight, CreateRole, CreateProject
from .database import async_session, async_engine
from .models import Base
from contextlib import asynccontextmanager
from sqlalchemy.exc import IntegrityError

import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        # init rights
        init_rights = [
            CreateRight(
                name="read",
                description="Read rights",
                claim_key="aii_test1",
                claim_value="lol",
            ),
            CreateRight(
                name="write",
                description="Write rights",
                claim_key="aii_test1",
                claim_value="rofl",
            ),
            CreateRight(
                name="delete",
                description="Delete rights",
                claim_key="aii_test2",
                claim_value="hdgdl",
            ),
        ]
        for right in init_rights:
            try:
                await create_rights(session, right)
            except IntegrityError:
                logger.warning(f"Right {right} already exists")
                await session.rollback()
        # init roles
        init_roles = [
            CreateRole(name="admin", description="Admin role"),
            CreateRole(name="read-only", description="Read only role"),
        ]
        for role in init_roles:
            try:
                await create_roles(session, role)
            except IntegrityError:
                logger.warning(f"Role {role} already exists")
                await session.rollback()
        # init role mappings
        role_admin = await get_roles(session, name="admin")
        right_read = await get_rights(session, name="read")
        right_write = await get_rights(session, name="write")
        right_delete = await get_rights(session, name="delete")

        await create_roles_rights_mapping(session, role_admin[0].id, right_read[0].id)
        await create_roles_rights_mapping(session, role_admin[0].id, right_write[0].id)
        await create_roles_rights_mapping(session, role_admin[0].id, right_delete[0].id)

        # init project
        try:
            admin_project = await create_project(
                session,
                project=CreateProject(
                    name="admin", description="Initial admin project"
                ),
            )
        except IntegrityError:
            logger.warning(f"Initial admin project already exists")
            await session.rollback()
            role_admin = await get_roles(session, name="admin")
            admin_project = await get_projects(session, name="admin")
            admin_project = admin_project[0]

        await create_users_projects_roles_mapping(
            session,
            project_id=admin_project.id,
            role_id=role_admin[0].id,
            keycloak_id="bd1d8eb5-49f1-48b9-828b-9f3771691eb5",
        )

        # TODO cread from configmap
    yield  # This yield separates startup from shutdown code
    # Code here would run after the application stops


tags_metadata = [
    {
        "name": "Projects",
        "description": "Create, delete and modify projects",
    },
    {
        "name": "Aii",
        "description": "Retrive authorization related information",
    },
]

app = FastAPI(
    root_path="/aii",
    title="access-information-interface",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

app.include_router(aii_router, prefix="/aii")
app.include_router(projects_router, prefix="/projects")
