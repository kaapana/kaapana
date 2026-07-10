"""
Re-key existing project datastores from the 0.6.x name-based scheme to the 0.7.x short_id-based scheme.

    0.6.x: bucket project-<name>     / index project_<name>
    0.7.x: bucket project-<short_id> / index project_<short_id>

This is a one-off step of the 0.6.x -> 0.7.x migration. 
Copy it into the running Access Information Interface pod and run it there. 
It reuses that pod's MinIO/OpenSearch clients, credentials and database connection:

    NS=<services_namespace>
    POD=$(kubectl get pods -n $NS -l app.kubernetes.io/name=access-information-interface -o name | head -1)
    kubectl exec -i -n $NS "$POD" -c access-information-interface   -- sh -c 'cd /app && python3 -' < utils/migration-chart/docker/files/rekey_projects.py

* Minio objects are copied into the new buckets (and the old buckets are removed).
* OpenSearch gets an alias project_<short_id> pointing at the existing project_<name> index. 
* Both steps are idempotent: re-running skips projects that are already migrated. 
* Note that the admin project keeps short_id "admin", so its datastore names are unchanged and it is skipped.
"""

import asyncio
import logging

from minio.commonconfig import CopySource

from app.database import async_session
from app.projects.crud import get_projects
from app.projects.minio import get_minio_helper
from app.projects.opensearch import OpenSearchHelper
from app.projects.schemas import Project

from kaapanapy.helper import get_project_user_access_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("project-rekey")


async def _rekey_minio(minio_helper, project: Project, session) -> None:
    client = minio_helper.minio_client
    old_bucket = f"project-{project.name}"
    new_bucket = project.s3_bucket

    old_exists = client.bucket_exists(old_bucket)

    # Create the new bucket and its (UUID-keyed) access policies (idempotent)
    await minio_helper.setup_new_project(project, session)

    if not old_exists:
        logger.info(f"[{project.name}] MinIO: no old bucket {old_bucket!r}, skipping copy")
        return

    copied = 0
    for obj in client.list_objects(old_bucket, recursive=True):
        client.copy_object(
            new_bucket, obj.object_name, CopySource(old_bucket, obj.object_name)
        )
        copied += 1
    logger.info(f"[{project.name}] MinIO: copied {copied} objects {old_bucket} -> {new_bucket}")

    for obj in client.list_objects(old_bucket, recursive=True):
        client.remove_object(old_bucket, obj.object_name)
    client.remove_bucket(old_bucket)
    logger.info(f"[{project.name}] MinIO: removed old bucket {old_bucket}")


async def _rekey_opensearch(os_helper: OpenSearchHelper, project: Project) -> None:
    client = os_helper.os_client
    old_index = f"project_{project.name}"
    new_alias = project.opensearch_index

    if not client.indices.exists(index=old_index):
        logger.info(f"[{project.name}] OpenSearch: no old index {old_index!r}, skipping alias")
        return
    if client.indices.exists_alias(name=new_alias):
        logger.info(f"[{project.name}] OpenSearch: alias {new_alias!r} already exists, skipping")
        return
    if client.indices.exists(index=new_alias):
        # On deploy, the aii init-projects job creates an empty physical index project_<short_id> before this re-key runs
        # If it is empty, drop it, so we can alias the new name onto the real (old) index that holds the migrated metadata
        # If it already has documents (0.7 data), leave it
        doc_count = client.count(index=new_alias).get("count", 0)
        if doc_count == 0:
            client.indices.delete(index=new_alias)
            logger.info(
                f"[{project.name}] OpenSearch: removed empty index {new_alias!r} "
                "so it can alias the migrated data"
            )
        else:
            logger.warning(
                f"[{project.name}] OpenSearch: {new_alias!r} exists as a real index "
                f"with {doc_count} docs, skipping alias to avoid data loss"
            )
            return

    await os_helper._set_alias(old_index, new_alias)


async def rekey_all_projects() -> None:
    minio_helper = get_minio_helper()
    os_helper = OpenSearchHelper(access_token=get_project_user_access_token())

    async with async_session() as session:
        orm_projects = await get_projects(session)

    for orm in orm_projects:
        try:
            project = Project.model_validate(orm)
        except Exception as e:
            logger.warning(f"Skipping project {getattr(orm, 'name', '?')}: cannot load ({e})")
            continue

        if project.short_id == project.name:
            logger.info(f"[{project.name}] short_id == name, nothing to re-key")
            continue

        logger.info(f"[{project.name}] re-keying to short_id {project.short_id}")
        async with async_session() as session:
            await _rekey_minio(minio_helper, project, session)
        await _rekey_opensearch(os_helper, project)

    logger.info("Project re-key finished.")


if __name__ == "__main__":
    asyncio.run(rekey_all_projects())
