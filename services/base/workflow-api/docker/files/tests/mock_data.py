import argparse
import asyncio
import traceback
from random import choice, randint

from app import schemas
from app.schemas import Label, Workflow, WorkflowCreate
from app.validation.config_definition import (
    ConfigDefinition,
    WorkflowParameter,
    WorkflowParameterUI,
)

from .common import create_workflow, delete_workflow, get_all_workflows

semaphore = asyncio.Semaphore(5)

PARAMETERS = {
    "nnunet-training": [
        WorkflowParameter(
            title="Epochs",
            description="How many epochs of nnUnet model training should be run?",
            env_variable_name="EPOCHS",
            required=True,
            ui_params=WorkflowParameterUI(type="number-field", default=10, minimum=0),
        ),
        WorkflowParameter(
            title="Learning Rate",
            description="Initial nnUnet model training learning rate?",
            env_variable_name="LR",
            ui_params=WorkflowParameterUI(
                type="number-field", default=0.001, maximum=1, minimum=0
            ),
        ),
        WorkflowParameter(
            title="Use Preprocessing",
            description="Should the data be preprocessed in train-nnUnet task? (Default: True) Very Long Testing Description to see how it looks in the UI",
            env_variable_name="USE_PREPROCESSING",
            required=True,
            ui_params=WorkflowParameterUI(type="switch"),
        ),
        WorkflowParameter(
            title="Included Organs",
            description="Choose organs to include in segmentation",
            env_variable_name="included_organs",
            ui_params=WorkflowParameterUI(
                type="multiselect",
                options=["lung", "liver", "spleen", "kidney"],
            ),
        ),
    ],
    "validation": [
        WorkflowParameter(
            title="Validation Algorithm",
            description="Choose validation algorithm from the selection",
            env_variable_name="validation_algorithm",
            ui_params=WorkflowParameterUI(
                type="select",
                default="dcmifo",
                options=["dcmifo", "dyvoid", "valvalval"],
            ),
        ),
    ],
    "dataset-preparation": [
        WorkflowParameter(
            title="Dataset",
            description="Select dataset to run the workflow",
            env_variable_name="GetInputData",
            required=True,
            ui_params=WorkflowParameterUI(type="string", default="/data/input"),
        ),
    ],
}

DEFINITION = """
# dag.py content of a python file
    from airflow import DAG
    from airflow.operators.bash import BashOperator
    from datetime import datetime

    default_args = {
        'owner': 'airflow',
        'start_date': datetime(2023, 1, 1),
        'retries': 1,
    }
    with DAG('segmentation_workflow', default_args=default_args, schedule_interval=None) as dag:
        preprocess = BashOperator(
            task_id='preprocess',
            bash_command='echo Preprocessing data...'
        )
        segment = BashOperator(
            task_id='segment',
            bash_command='echo Segmenting organs...'
        )
        postprocess = BashOperator(
            task_id='postprocess',
            bash_command='echo Postprocessing results...'
        )
        preprocess >> segment >> postprocess
"""

PREDETERMINED_WORKFLOWS = [
    WorkflowCreate(
        title="Segmentation Workflow",
        definition=DEFINITION,
        workflow_engine="Airflow",
        config_definition=ConfigDefinition(
            workflow_parameters=PARAMETERS,
        ),
        labels=[
            Label(
                key="kaapana-ui.description",
                value="Execute Total Segmentator on DICOM images, producing labeled organ masks.",
            ),
            Label(key="kaapana-ui.category", value="segmentation"),
            Label(key="kaapana-ui.provider", value="dkfz-mic"),
        ],
    ),
    WorkflowCreate(
        title="Classification Workflow",
        definition=DEFINITION,
        workflow_engine="Docker",
        config_definition=ConfigDefinition(
            workflow_parameters=PARAMETERS,
        ),
        labels=[
            Label(
                key="kaapana-ui.description",
                value="Classify medical scans using AI-based tumor detection.",
            ),
            Label(key="kaapana-ui.category", value="classification"),
            Label(key="kaapana-ui.provider", value="google-ai"),
        ],
    ),
    WorkflowCreate(
        title="Omics Data Analysis",
        definition=DEFINITION,
        workflow_engine="Airflow",
        config_definition=ConfigDefinition(
            workflow_parameters=PARAMETERS,
        ),
        labels=[
            Label(
                key="kaapana-ui.description",
                value="Pipeline for genomics and proteomics data preprocessing and feature extraction.",
            ),
            Label(key="kaapana-ui.category", value="omics"),
            Label(key="kaapana-ui.category", value="data-preprocessing"),
            Label(key="kaapana-ui.provider", value="openai"),
        ],
    ),
    WorkflowCreate(
        title="Hybrid Imaging Workflow",
        definition=DEFINITION,
        workflow_engine="Docker",
        config_definition=ConfigDefinition(
            workflow_parameters=PARAMETERS,
        ),
        labels=[
            Label(
                key="kaapana-ui.description",
                value="Executes segmentation and classification on hybrid imaging datasets.",
            ),
            Label(key="kaapana-ui.category", value="segmentation"),
            Label(key="kaapana-ui.category", value="classification"),
            Label(key="kaapana-ui.provider", value="dkfz-mic"),
            Label(key="kaapana-ui.provider", value="openai"),
        ],
    ),
    WorkflowCreate(
        title="Data Preprocessing Pipeline With A Very Long Name That Someone Will Definitely Do: Continue Here To Test UI Handling of Long Names",
        definition=DEFINITION,
        workflow_engine="Airflow",
        config_definition=ConfigDefinition(
            workflow_parameters=PARAMETERS,
        ),
        labels=[
            Label(
                key="kaapana-ui.description",
                value="Performs normalization, augmentation, and feature extraction from raw data. Very Long Description to see how it looks in the UI",
            ),
            Label(key="kaapana-ui.category", value="data-preprocessing"),
            Label(key="kaapana-ui.provider", value="google-ai"),
        ],
    ),
]


# --- GENERATED WORKFLOWS FOR UI SCROLLING / TESTING ---
MATURITY_OPTIONS = ["experimental", "stable"]
PROVIDERS = ["dkfz-mic", "google-ai", "openai", "nvidia", "ibm"]
CATEGORIES = [
    "segmentation",
    "classification",
    "data-preprocessing",
    "omics",
    "registration",
    "visualization",
]

GENERATED_WORKFLOWS = []
for i in range(1, 31):
    title = f"Generated Workflow {i:02d}"
    labels = [
        Label(
            key="kaapana-ui.description",
            value=f"Auto-generated workflow #{i} for UI testing.",
        ),
        Label(key="kaapana-ui.category", value=choice(CATEGORIES)),
        Label(key="kaapana-ui.provider", value=choice(PROVIDERS)),
        Label(key="kaapana-ui.maturity", value=choice(MATURITY_OPTIONS)),
    ]
    wf = WorkflowCreate(
        title=title,
        definition=DEFINITION,
        workflow_engine=choice(["Airflow", "Docker"]),
        config_definition=ConfigDefinition(workflow_parameters=PARAMETERS),
        labels=labels,
    )
    GENERATED_WORKFLOWS.append(wf)


async def create_generated_workflows_and_runs():
    """Create generated workflows and some runs for UI testing."""
    print("\n=== Creating Generated Workflows ===")
    # create generated workflows
    # We'll create multiple versions for some workflows to test version grouping
    for workflow in GENERATED_WORKFLOWS:
        async with semaphore:
            try:
                # create initial version
                response = await create_workflow(workflow_create=workflow)
                response.raise_for_status()
                created_workflow = Workflow(**response.json())
                print(f"Created generated workflow: {created_workflow.title} (v{created_workflow.version})")

                # randomly create 1-3 additional versions for ~30% of generated workflows
                if randint(1, 10) <= 3:
                    extra_versions = randint(1, 3)
                    for _ in range(extra_versions):
                        # re-create workflow (server should bump version)
                        resp2 = await create_workflow(workflow_create=workflow)
                        resp2.raise_for_status()
                        created2 = Workflow(**resp2.json())
                        print(f"  -> Created extra version: {created2.title} (v{created2.version})")

            except Exception as e:
                print(f"Failed to create generated workflow '{workflow.title}': {e}")
                traceback.print_exc()
            await asyncio.sleep(0.1)

    # create some workflow runs for a subset
    print("\n=== Creating Sample Workflow Runs ===")
    # We will use the first 10 generated workflows to create runs
    # fetch all workflows to know available versions
    from .common import create_workflow_run, get_all_workflows

    try:
        resp = await get_all_workflows()
        resp.raise_for_status()
        all_wfs = [Workflow(**wf) for wf in resp.json()]
    except Exception:
        all_wfs = []

    # group workflows by title -> available versions
    wf_map = {}
    for wf in all_wfs:
        wf_map.setdefault(wf.title, []).append(wf.version)

    titles = list(wf_map.keys())[:10]
    for wf_title in titles:
        versions = sorted(wf_map.get(wf_title, [1]))
        # create 1-6 runs distributed across available versions
        runs_to_create = randint(1, 6)
        for _ in range(runs_to_create):
            async with semaphore:
                try:
                    # pick a random existing version for this title
                    chosen_version = choice(versions)
                    run_payload = schemas.WorkflowRunCreate(
                        workflow=schemas.WorkflowRef(title=wf_title, version=chosen_version),
                        labels=[],
                        config_definition=None,
                    )
                    await create_workflow_run(run_payload)
                    print(f"Created run for {wf_title} v{chosen_version}")
                except Exception as e:
                    print(f"Failed to create run for {wf_title}: {e}")
                    traceback.print_exc()
                await asyncio.sleep(0.05)


async def create_predetermined_workflows():
    """Create all predetermined workflows."""
    for workflow in PREDETERMINED_WORKFLOWS:
        async with semaphore:
            try:
                response = await create_workflow(workflow_create=workflow)
                response.raise_for_status()
                created_workflow = Workflow(**response.json())
                print(
                    f"Created predetermined workflow: {created_workflow.title} (v{created_workflow.version})"
                )
            except Exception as e:
                print(
                    f"Failed to create predetermined workflow '{workflow.title}': {e}"
                )
                traceback.print_exc()
            await asyncio.sleep(0.5)


async def create_all_workflows():
    """
    Create workflows based on flags.
    """
    print("\n=== Creating Predetermined Workflows ===")
    await create_predetermined_workflows()


async def delete_all_workflows():
    try:
        response = await get_all_workflows()
        response.raise_for_status()
        workflows = [Workflow(**wf) for wf in response.json()]
        for wf in workflows:
            response = await delete_workflow(title=wf.title, version=wf.version)
            response.raise_for_status()
            print(f"DELETED -> Title: {wf.title}, Version: {wf.version}")
    except Exception as e:
        print(f"Failed to delete workflows: {e}")


async def main():
    parser = argparse.ArgumentParser(
        description="Workflow CLI (async) for generating or deleting workflows"
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("generate", help="Generate workflows")
    subparsers.add_parser(
        "generate-many", help="Generate many workflows and sample runs for UI testing"
    )
    subparsers.add_parser("delete", help="Delete all workflows")

    args = parser.parse_args()

    if args.command == "generate":
        await create_all_workflows()
    elif args.command == "generate-many":
        await create_generated_workflows_and_runs()
    elif args.command == "delete":
        await delete_all_workflows()
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
