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

    logger.info(f"Submitting workflow '{workflow_data.title}' to {endpoint}")
    logger.debug(f"Workflow data: {workflow_data.model_dump_json(indent=2)}")

    try:
        response = await client.post(
            endpoint,
            json=workflow_data.model_dump(mode="json"),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        result = response.json()
        logger.info(
            f"Successfully submitted workflow '{result.get('title')}' "
            f"version {result.get('version')}"
        )
        return True

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            logger.warning(f"Workflow already exists: {e.response.text}")
            return True  # Consider existing workflow as success
        logger.error(f"HTTP error submitting workflow: {e.response.text}")
        return False
    except httpx.RequestError as e:
        logger.error(f"Error submitting workflow: {e}")
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
            client, settings.workflow_api_url, workflow_data
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
