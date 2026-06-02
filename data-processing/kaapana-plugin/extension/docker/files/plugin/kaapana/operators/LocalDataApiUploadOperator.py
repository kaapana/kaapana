import asyncio
import glob
import json
import os
from pathlib import Path
from uuid import uuid4

import httpx
import requests

from data_api import DataClient
from kaapana.blueprints.kaapana_global_variables import (
    AIRFLOW_WORKFLOW_DIR,
    BATCH_NAME,
)
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.helper.HelperOpensearch import DicomTags
from kaapanapy.settings import KaapanaSettings


class LocalDataApiUploadOperator(KaapanaPythonBaseOperator):
    """
    Creates entities in the data-api for each series and uploads metadata and thumbnails.

    For each series this operator creates a data entity (with PACS storage
    coordinates) and attaches the extracted DICOM metadata, plus — when present —
    a thumbnail artifact, permissions metadata, and validation results.
    """

    def start(self, ds, **kwargs):
        skip = False  # Set to false to enable uploading to data-api
        if skip:
            print(
                "This is a demo operator showcasing the new and experimental Data API.\n"
                "Currently nothing happens since the operator is in skip mode.\n"
                "If you want to try the new feature, open "
                "LocalDataApiUploadOperator.py in code server for airflow and set "
                "skip to False."
            )
            return

        asyncio.run(self._upload(**kwargs))

    async def _upload(self, **kwargs):
        kaapana_settings = KaapanaSettings()

        # Register the DICOM metadata schema if not already registered
        dicom_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "DICOM Metadata",
            "description": "DICOM metadata extracted from DICOM files",
            "additionalProperties": True,
        }

        # Register the Permissions schema
        permissions_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "Permissions",
            "description": "Permissions and project associations for the entity",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Project ID that owns this entity",
                },
                "owner": {
                    "type": ["string", "null"],
                    "description": "Owner of the entity, null by default",
                },
            },
            "additionalProperties": True,
        }

        # Register the Validation Results schema (generic, permissive)
        validation_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "Validation Results",
            "description": "Results produced by validators, potentially including HTML reports",
            "additionalProperties": True,
        }

        async with DataClient() as data_api:
            for schema_key, schema, label in (
                ("dicom-series", dicom_schema, "DICOM"),
                ("permissions", permissions_schema, "Permissions"),
                ("dicom-series-validation", validation_schema, "Validation"),
            ):
                try:
                    await data_api.register_metadata_schema(schema_key, schema)
                    print(f"Successfully registered {label} metadata schema")
                except httpx.HTTPError as e:
                    # Schema might already exist, continue anyway
                    print(
                        f"Note: Could not register {label} schema (may already exist): {e}"
                    )

            batch_dir = (
                Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME
            )
            batch_folder = [f for f in glob.glob(os.path.join(batch_dir, "*"))]

            for batch_element_dir in batch_folder:
                json_dir = Path(batch_element_dir) / self.metadata_dir
                thumbnail_dir = Path(batch_element_dir) / self.thumbnail_dir

                json_files = [f for f in json_dir.glob("*.json")]
                assert len(json_files) == 1
                metadata_file = json_files[0]

                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

                series_uid = metadata.get(DicomTags.series_uid_tag)
                study_uid = metadata.get(DicomTags.study_uid_tag)
                instance_uid = metadata.get(DicomTags.SOPInstanceUID_tag)

                if not series_uid or not study_uid:
                    print(
                        f"Warning: Missing series UID or study UID in metadata file {metadata_file}"
                    )
                    continue

                # Generate UUID for entity ID
                entity_id = str(uuid4())

                # Create or update entity with metadata and PACS storage coordinates
                entity_data = {
                    "id": entity_id,
                    "storage_coordinates": [
                        {
                            "type": "pacs",
                            "pacs_id": f"http://dicom-web-filter-service.{kaapana_settings.services_namespace}.svc:8080",
                            "study_uid": study_uid,
                            "series_uid": series_uid,
                            "instance_uid": instance_uid,
                        }
                    ],
                    "metadata": [
                        {"key": "dicom-series", "data": metadata, "artifacts": []}
                    ],
                }

                try:
                    await data_api.create_entity(entity_data)
                    print(
                        f"Successfully created/updated entity {entity_id} for series {series_uid}"
                    )
                except httpx.HTTPError as e:
                    print(f"Error creating entity for series {series_uid}: {e}")
                    continue

                # Upload thumbnail as artifact if it exists
                thumbnails = [f for f in thumbnail_dir.glob("*.png")]
                if thumbnails:
                    assert len(thumbnails) == 1
                    thumbnail_path = thumbnails[0]

                    try:
                        with open(thumbnail_path, "rb") as thumbnail_file:
                            await data_api.upload_artifact(
                                entity_id,
                                "dicom-series",
                                "thumbnail",
                                thumbnail_file,
                                filename=thumbnail_path.name,
                                content_type="image/png",
                            )
                        print(
                            f"Successfully uploaded thumbnail for series {series_uid}"
                        )
                    except httpx.HTTPError as e:
                        print(f"Error uploading thumbnail for series {series_uid}: {e}")

                # Add permissions metadata if project was found
                # Extract project name and fetch project details (aii-service, NOT data-api)
                project_id = metadata.get(DicomTags.clinical_trial_protocol_id_tag)
                project = None
                if project_id:
                    try:
                        response = requests.get(
                            f"http://aii-service.{kaapana_settings.services_namespace}.svc:8080/projects"
                        )
                        response.raise_for_status()
                        projects = response.json()
                        matching_projects = [
                            p for p in projects if p.get("id") == project_id
                        ]
                        if matching_projects:
                            project = matching_projects[0]
                        else:
                            print(f"Warning: Project with id '{project_id}' not found")
                    except requests.exceptions.RequestException as e:
                        print(f"Warning: Failed to fetch projects: {e}")

                if project:
                    try:
                        await data_api.attach_metadata(
                            entity_id,
                            "permissions",
                            {"project": project.get("id"), "owner": None},
                        )
                        print(
                            f"Added permissions metadata to entity {entity_id} for project {project.get('id')}"
                        )
                    except httpx.HTTPError as e:
                        print(
                            f"Error adding permissions metadata for entity {entity_id}: {e}"
                        )

                # Add validation results
                # Append validation metadata and upload HTML report artifacts
                validator_results_dir = Path(batch_element_dir) / self.validation_dir
                validation_reports = [f for f in validator_results_dir.glob("*.html")]

                if validation_reports:
                    # Prefer validator-produced JSON as the metadata payload
                    validation_json_files = [
                        f for f in validator_results_dir.glob("*.json")
                    ]
                    validation_payload = None
                    if validation_json_files:
                        try:
                            with open(validation_json_files[0], "r") as vf:
                                validation_payload = json.load(vf)
                        except Exception as e:
                            print(
                                f"Warning: Failed to load validation JSON '{validation_json_files[0]}': {e}"
                            )

                    # Fallback to a minimal payload with report names if JSON is unavailable
                    if validation_payload is None:
                        validation_payload = {
                            "reports": [report.name for report in validation_reports],
                            "source": "DcmValidatorOperator",
                        }

                    try:
                        await data_api.attach_metadata(
                            entity_id, "dicom-series-validation", validation_payload
                        )
                        print(f"Added validation metadata to entity {entity_id}")

                        # Upload each HTML report as an artifact under the 'validation' metadata
                        for report_path in validation_reports:
                            artifact_id = f"report-{report_path.stem}"
                            try:
                                with open(report_path, "rb") as report_file:
                                    await data_api.upload_artifact(
                                        entity_id,
                                        "dicom-series-validation",
                                        artifact_id,
                                        report_file,
                                        filename=report_path.name,
                                        content_type="text/html",
                                    )
                                print(
                                    f"Uploaded validation report artifact '{artifact_id}' for entity {entity_id}"
                                )
                            except httpx.HTTPError as e:
                                print(
                                    f"Error uploading validation report '{report_path.name}' for entity {entity_id}: {e}"
                                )
                    except httpx.HTTPError as e:
                        print(
                            f"Error adding validation metadata for entity {entity_id}: {e}"
                        )

    def __init__(
        self,
        dag,
        metadata_dir: str,
        thumbnail_dir: str,
        validation_dir: str,
        name: str = "upload-series-to-data-api",
        **kwargs,
    ):
        """
        :param metadata_dir: out-dir of the DICOM-to-JSON operator (series metadata).
        :param thumbnail_dir: out-dir of the thumbnail operator.
        :param validation_dir: out-dir of the DICOM validator operator.
        """
        self.metadata_dir = metadata_dir
        self.thumbnail_dir = thumbnail_dir
        self.validation_dir = validation_dir
        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
