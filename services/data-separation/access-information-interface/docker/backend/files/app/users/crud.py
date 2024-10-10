from app.models import Projects, Roles, UsersProjectsRoles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_user_projects(session: AsyncSession, user_id: str):
    # Query Projects based on the project_id through the UsersProjectsRoles table
    stmt = (
        select(UsersProjectsRoles, Projects, Roles)
        .join(Projects, UsersProjectsRoles.project_id == Projects.id)
        .join(Roles, UsersProjectsRoles.role_id == Roles.id)
        .filter(UsersProjectsRoles.keycloak_id == user_id)
    )

    # Execute the query asynchronously
    result = await session.execute(stmt)
    # Fetch all the projects
    projects = result.fetchall()

    return projects
