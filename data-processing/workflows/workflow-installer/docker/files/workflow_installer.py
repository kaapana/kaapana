#!/usr/bin/env python3
"""
Workflow Installer Script

Submits workflow definitions to the Kaapana Workflow API.
Reads workflow definition and metadata from environment variables or files.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

import httpx
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings
from schemas import WorkflowCreate
from validation_rules import ValidationConfig, WorkflowValidator

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Configuration settings loaded from environment variables."""

    workflow_api_url: str = Field(
        default="",
        description="Base URL of the Workflow API",
    )
    workflow_dir: Path = Field(
        default=Path("/workflows"), description="Directory containing workflow files"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(
        default=5, description="Maximum number of retries for API calls"
    )
    enforce_init_workflows: bool = Field(
        default=True,
        description="When True, PATCH an existing workflow with the same title; when False, leave it as-is.",
    )


def load_workflow_definition(workflow_dir: Path) -> str:
    """
    Load workflow definition from all files in the directory (except workflow.json).

    Concatenates all non-metadata files into a single definition string.
    Files are separated by comments indicating the filename.
    """
    # Get all files except workflow.json
    all_files = [
        f for f in workflow_dir.iterdir() if f.is_file() and f.name != "workflow.json"
    ]

    if not all_files:
        raise FileNotFoundError(
            f"No workflow definition files found in {workflow_dir}. "
            "Directory should contain at least one file besides workflow.json"
        )

    # Sort files for consistent ordering
    all_files = sorted(all_files)

    logger.info(f"Loading {len(all_files)} workflow definition file(s)")

    # Concatenate all files
    definition_parts = []
    for file_path in all_files:
        logger.info(f"  - {file_path.name}")
        with open(file_path, "r") as f:
            content = f.read()

        # Add file separator comment (only if multiple files)
        if len(all_files) > 1:
            definition_parts.append(f"# ==== {file_path.name} ====\n")

        definition_parts.append(content)

        # Add newline between files
        if len(all_files) > 1:
            definition_parts.append("\n\n")

    return "".join(definition_parts)


def load_workflow_metadata(metadata_path: Path) -> dict:
    """Load workflow metadata (parameters, labels, etc.) from JSON file."""
    logger.info(f"Loading workflow metadata from {metadata_path}")
    with open(metadata_path, "r") as f:
        return json.load(f)


async def submit_workflow(
    client: httpx.AsyncClient,
    api_url: str,
    workflow_data: WorkflowCreate,
    enforce: bool,
) -> bool:
    """
    Submit workflow to the Workflow API.

    Args:
        client: Async HTTP client
        api_url: Base URL of the workflow API
        workflow_data: Validated workflow data schema

    Returns:
        True if submission successful, False otherwise
    """
    endpoint = f"{api_url}/workflows"
    title = workflow_data.title

    logger.info(f"Submitting workflow '{title}' to {endpoint}")
    logger.debug(f"Workflow data: {workflow_data.model_dump_json(indent=2)}")

    try:
        response = await client.post(
            endpoint,
            json=workflow_data.model_dump(mode="json"),
            headers={"Content-Type": "application/json"},
        )
    except httpx.RequestError as e:
        logger.error(f"Error submitting workflow: {e}")
        return False

    if response.status_code in (200, 201):
        result = response.json()
        action = "Created" if response.status_code == 201 else "Already up to date"
        logger.info(
            f"{action}: workflow '{result.get('title')}' "
            f"(id={result.get('id')}, increment={result.get('increment')})"
        )
        return True

    if response.status_code == 409:
        return await _handle_conflict(client, api_url, workflow_data, response, enforce)

    logger.error(
        f"HTTP {response.status_code} submitting workflow '{title}': {response.text}"
    )
    return False


async def _handle_conflict(
    client: httpx.AsyncClient,
    api_url: str,
    workflow_data: WorkflowCreate,
    conflict_response: httpx.Response,
    enforce: bool,
) -> bool:
    """Dispatch 409 handling based on the response body shape and the enforce flag."""
    title = workflow_data.title
    try:
        detail = conflict_response.json().get("detail", {})
    except ValueError:
        logger.error(
            f"Conflict on '{title}' with unparseable body: {conflict_response.text}"
        )
        return False

    existing = detail.get("existing_workflow", {}) if isinstance(detail, dict) else {}

    if "workflow_engine" in existing:
        logger.error(
            f"Cannot install workflow '{title}': engine mismatch (existing workflow_engine='{existing.get('workflow_engine')}', incoming='{detail.get('incoming_workflow_engine')}'). Engine is immutable."
        )
        return False

    if not enforce:
        logger.warning(
            f"Workflow '{title}' exists with different content; ENFORCE_INIT_WORKFLOWS=False, leaving as-is."
        )
        return True

    existing_id = existing.get("id")
    if not existing_id:
        logger.error(
            f"Conflict on '{title}' but no existing_workflow.id in body: {detail}"
        )
        return False

    return await _patch_workflow(client, api_url, existing_id, workflow_data)


async def _patch_workflow(
    client: httpx.AsyncClient,
    api_url: str,
    workflow_id: str,
    workflow_data: WorkflowCreate,
) -> bool:
    """PATCH content fields (definition, parameters, labels) onto an existing workflow."""
    title = workflow_data.title
    endpoint = f"{api_url}/workflows/{workflow_id}"
    payload = workflow_data.model_dump(
        mode="json", include={"definition", "workflow_parameters", "labels"}
    )

    logger.info(f"ENFORCE_INIT_WORKFLOWS=True — PATCHing '{title}' at {endpoint}")
    try:
        response = await client.patch(
            endpoint, json=payload, headers={"Content-Type": "application/json"}
        )
    except httpx.RequestError as e:
        logger.error(f"Error PATCHing workflow '{title}': {e}")
        return False

    if response.status_code == 200:
        result = response.json()
        logger.info(
            f"PATCH succeeded: workflow '{result.get('title')}' "
            f"now at increment={result.get('increment')}"
        )
        return True

    if response.status_code == 403:
        logger.error(
            f"PATCH on '{title}' returned 403. The workflow-api has DEV_MODE=False, "
            "but the installer is configured with ENFORCE_INIT_WORKFLOWS=True. "
            "Resolve the conflicting config."
        )
        return False

    logger.error(
        f"PATCH on '{title}' returned HTTP {response.status_code}: {response.text}"
    )
    return False


async def check_api_health(client: httpx.AsyncClient, api_url: str) -> bool:
    """
    Check if the Workflow API is reachable and healthy.

    Args:
        client: Async HTTP client
        api_url: Base URL of the workflow API

    Returns:
        True if API is healthy, False otherwise
    """
    health_endpoint = f"{api_url}/health"

    logger.info(f"Checking workflow API health at {health_endpoint}")

    try:
        response = await client.get(health_endpoint)
        response.raise_for_status()
        logger.info("Workflow API is healthy and reachable")
        return True
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Workflow API health check failed with status {e.response.status_code}: {e.response.text}"
        )
        return False
    except httpx.RequestError as e:
        logger.error(f"Cannot reach Workflow API at {api_url}: {e}")
        return False


def load_and_validate_workflow(settings: Settings) -> tuple[str, dict]:
    """Load and validate workflow files."""
    metadata_file = settings.workflow_dir / "workflow.json"

    if not metadata_file.exists():
        logger.error(f"Metadata file not found: {metadata_file}")
        sys.exit(1)

    try:
        definition = load_workflow_definition(settings.workflow_dir)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    metadata = load_workflow_metadata(metadata_file)

    title = metadata.get("title")
    if not title:
        logger.error("Workflow title is required in metadata")
        sys.exit(1)

    if not definition:
        logger.error("Workflow definition is empty")
        sys.exit(1)

    return definition, metadata


def create_and_validate_workflow_schema(
    definition: str, metadata: dict
) -> WorkflowCreate:
    """Create and validate workflow schema."""
    logger.info("\nValidating workflow schema...")
    try:
        workflow_data = WorkflowCreate(
            title=metadata["title"],
            definition=definition,
            workflow_engine=metadata["workflow_engine"],
            workflow_parameters=metadata.get("workflow_parameters", []),
            labels=metadata.get("labels", []),
        )
        log_workflow_info(workflow_data)
        return workflow_data
    except ValidationError as e:
        logger.error("\033[31mWorkflow validation failed:\033[0m")
        for error in e.errors():
            loc = " -> ".join(str(loc_part) for loc_part in error["loc"])
            logger.error(f"  {loc}: {error['msg']}")
        sys.exit(1)


def log_workflow_info(workflow_data: WorkflowCreate) -> None:
    """Log workflow information."""
    logger.info(f"\033[32m✓ Workflow '{workflow_data.title}' is valid!\033[0m")
    logger.info(f"  - Workflow engine: {workflow_data.workflow_engine}")
    logger.info(f"  - Definition size: {len(workflow_data.definition)} bytes")

    # Display parameters
    params = workflow_data.workflow_parameters or []
    logger.info(f"  - Parameters: {len(params)}")
    if params:
        for param in params:
            param_type = param.ui_form.type
            required = "required" if param.ui_form.required else "optional"
            logger.info(f"    • {param.env_variable_name} ({param_type}, {required})")

    # Display labels
    labels = workflow_data.labels or []
    logger.info(f"  - Labels: {len(labels)}")
    if labels:
        for label in labels:
            logger.info(f"    • {label.key}: {label.value}")


def run_validation_checks(
    settings: Settings, metadata: dict, workflow_engine: str
) -> None:
    """Run workflow validation checks."""
    logger.info("\nRunning validation checks...")
    validator = WorkflowValidator(ValidationConfig())
    validation_results = validator.validate_all(
        settings.workflow_dir, metadata, workflow_engine
    )

    # Display validation results
    for result in validation_results:
        if result.passed:
            logger.info(f"\033[32m  ✓ [{result.rule_name}] {result.message}\033[0m")
        elif result.severity == "error":
            logger.error(f"\033[31m  ✗ [{result.rule_name}] {result.message}\033[0m")
        elif result.severity == "warning":
            logger.warning(f"\033[33m  ⚠ [{result.rule_name}] {result.message}\033[0m")
        else:
            logger.info(f"  ℹ [{result.rule_name}] {result.message}")

    logger.info(f"\nValidation summary: {validator.get_summary()}")

    if validator.has_errors():
        logger.error("\033[31mValidation failed with errors!\033[0m")
        sys.exit(1)


async def process_workflow_submission(
    settings: Settings, workflow_data: WorkflowCreate
) -> None:
    """Handle workflow submission to API."""
    transport = httpx.AsyncHTTPTransport(retries=settings.max_retries)
    timeout = httpx.Timeout(settings.timeout)

    async with httpx.AsyncClient(transport=transport, timeout=timeout) as client:
        if not await check_api_health(client, settings.workflow_api_url):
            logger.error(
                "Workflow API health check failed. Please verify WORKFLOW_API_URL is correct."
            )
            sys.exit(1)

        success = await submit_workflow(
            client,
            settings.workflow_api_url,
            workflow_data,
            enforce=settings.enforce_init_workflows,
        )
        sys.exit(0 if success else 1)


async def main():
    """Main entry point for the workflow installer."""
    settings = Settings()

    logger.info(f"Workflow directory: {settings.workflow_dir}")
    logger.info(f"Workflow API URL: {settings.workflow_api_url}")

    # Load and validate workflow files
    definition, metadata = load_and_validate_workflow(settings)

    # Create and validate workflow schema
    workflow_data = create_and_validate_workflow_schema(definition, metadata)

    # Run validation checks
    run_validation_checks(settings, metadata, workflow_data.workflow_engine)

    # Submit workflow to API
    await process_workflow_submission(settings, workflow_data)


if __name__ == "__main__":
    asyncio.run(main())
