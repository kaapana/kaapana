import argparse
import asyncio
import traceback
from random import choice, randint

import httpx
from app import schemas
from app.schemas import (
    BooleanUIForm,
    FileUIForm,
    FloatUIForm,
    IntegerUIForm,
    Label,
    ListUIForm,
    StringUIForm,
    TermsUIForm,
    Workflow,
    WorkflowCreate,
    WorkflowParameter,
)

from .common import (
    create_workflow,
    delete_workflow,
    delete_workflow_run,
    get_all_workflow_runs,
    get_all_workflows,
)

semaphore = asyncio.Semaphore(5)

PARAMETERS: list[WorkflowParameter] = [
    WorkflowParameter(
        task_title="nnunet-training",
        env_variable_name="EPOCHS",
        ui_form=IntegerUIForm(
            type="int",
            title="Epochs",
            description="Specify the number of training epochs.",
            help="How many epochs of nnUnet model training should be run?",
            required=True,
            default=10,
            minimum=1,
            maximum=1000,
        ),
    ),
    WorkflowParameter(
        task_title="nnunet-training",
        env_variable_name="BATCH_SIZE",
        ui_form=IntegerUIForm(
            type="int",
            title="Batch Size",
            description="Number of samples per training batch.",
            help="Larger batch sizes require more memory but may improve training stability.",
            required=True,
            default=16,
            minimum=1,
            maximum=256,
        ),
    ),
    WorkflowParameter(
        task_title="nnunet-training",
        env_variable_name="LR",
        ui_form=FloatUIForm(
            type="float",
            title="Learning Rate",
            description="Initial nnUnet model training learning rate.",
            help="What should be the initial learning rate for nnUnet model training?",
            default=0.001,
            minimum=0.0001,
            maximum=1.0,
            required=True,
        ),
    ),
    WorkflowParameter(
        task_title="nnunet-training",
        env_variable_name="DROPOUT_RATE",
        ui_form=FloatUIForm(
            type="float",
            title="Dropout Rate",
            description="Dropout probability for regularization.",
            help="Higher values prevent overfitting but may reduce model capacity.",
            default=0.2,
            minimum=0.0,
            maximum=0.9,
            required=False,
        ),
    ),
    WorkflowParameter(
        task_title="nnunet-training",
        env_variable_name="USE_PREPROCESSING",
        ui_form=BooleanUIForm(
            type="bool",
            title="Use Preprocessing",
            description=(
                "Should the data be preprocessed in train-nnUnet task? (Default: True) "
                "Very long testing description to see how it looks in the UI."
            ),
            default=True,
            required=False,
            help="Enable or disable preprocessing step for training.",
            true_label="Enabled",
            false_label="Disabled",
        ),
    ),
    WorkflowParameter(
        task_title="nnunet-training",
        env_variable_name="ORGANS",
        ui_form=ListUIForm(
            type="list",
            title="Included Organs",
            description="Choose organs to include in segmentation.",
            help="Select one or more organs for segmentation from the list. At least one organ must be selected.",
            options=["lung", "liver", "spleen", "kidney", "heart", "brain"],
            multiselectable=True,
            required=True,
            default=["liver"],
        ),
    ),
    # === validation ===
    WorkflowParameter(
        task_title="validation",
        env_variable_name="VALIDATION_ALGO",
        ui_form=ListUIForm(
            type="list",
            title="Validation Algorithm",
            description="Choose validation algorithm from the selection.",
            help="Select the algorithm to use for validation.",
            options=["dcmifo", "dyvoid", "valvalval"],
            default="dcmifo",
            multiselectable=False,
            required=True,
        ),
    ),
    WorkflowParameter(
        task_title="validation",
        env_variable_name="CONFIDENCE_THRESHOLD",
        ui_form=FloatUIForm(
            type="float",
            title="Confidence Threshold",
            description="Minimum confidence score for validation acceptance.",
            help="Results below this threshold will be flagged for review.",
            default=0.8,
            minimum=0.5,
            maximum=1.0,
            required=True,
        ),
    ),
    # === dataset-preparation ===
    WorkflowParameter(
        task_title="dataset-preparation",
        env_variable_name="CONFIG_FILE",
        ui_form=FileUIForm(
            type="file",
            title="Configuration File",
            description="Upload a configuration JSON or YAML file.",
            help="Optional: Upload a custom configuration file to override default settings.",
            accept=".json,.yaml,.yml",
            multiple=False,
            default=None,
            required=False,
        ),
    ),
    WorkflowParameter(
        task_title="dataset-preparation",
        env_variable_name="DATASET_PATH",
        ui_form=StringUIForm(
            type="str",
            title="Dataset Path",
            description="Path to the dataset directory.",
            help="Must be an absolute path starting with /data/ or /datasets/",
            default="/data/input",
            regex_pattern="^/(data|datasets)/[a-zA-Z0-9_/-]+$",
            required=True,
        ),
    ),
    WorkflowParameter(
        task_title="dataset-preparation",
        env_variable_name="DATASET_NAME",
        ui_form=StringUIForm(
            type="str",
            title="Dataset Name",
            description="Unique identifier for this dataset.",
            help="Must be alphanumeric with underscores or hyphens only, 3-50 characters.",
            default="my_dataset",
            regex_pattern="^[a-zA-Z0-9_-]{3,50}$",
            required=True,
        ),
    ),
    WorkflowParameter(
        task_title="dataset-preparation",
        env_variable_name="EMAIL_NOTIFICATION",
        ui_form=StringUIForm(
            type="str",
            title="Notification Email",
            description="Email address for completion notifications.",
            help="Optional: receive an email when processing completes.",
            default="",
            regex_pattern="^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
            required=False,
        ),
    ),
    WorkflowParameter(
        task_title="dataset-preparation",
        env_variable_name="ACCEPT_TERMS",
        ui_form=TermsUIForm(
            type="terms",
            title="Accept Terms and Conditions",
            description="Terms and Conditions for Data Processing",
            help="You must accept the terms to proceed with workflow execution.",
            terms_text="I accept that this workflow will process medical imaging data and understand the privacy implications.",
            default=False,
            required=True,
        ),
    ),
]

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
        workflow_parameters=PARAMETERS,
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
        title="Clinical Trial Data Processing",
        definition=DEFINITION,
        workflow_engine="Airflow",
        workflow_parameters=[
            WorkflowParameter(
                task_title="data-processing",
                env_variable_name="PATIENT_CONSENT",
                ui_form=TermsUIForm(
                    type="terms",
                    title="Patient Consent Acknowledgment",
                    description="Legal requirements for clinical trial data processing",
                    help="Required by institutional review board (IRB) policies",
                    terms_text="I confirm that all patient data used in this workflow has appropriate informed consent for research use and complies with HIPAA regulations.",
                    default=False,
                    required=True,
                ),
            ),
            WorkflowParameter(
                task_title="data-processing",
                env_variable_name="STUDY_ID",
                ui_form=StringUIForm(
                    type="str",
                    title="Study Identifier",
                    description="Clinical trial study ID",
                    help="Must match the registered clinical trial identifier",
                    default="",
                    regex_pattern="^[A-Z]{2,4}-[0-9]{4,6}$",
                    required=True,
                ),
            ),
            WorkflowParameter(
                task_title="data-processing",
                env_variable_name="ANONYMIZE_DATA",
                ui_form=BooleanUIForm(
                    type="bool",
                    title="Anonymize Patient Data",
                    description="Remove all personally identifiable information (PII) from datasets",
                    default=True,
                    required=False,
                    help="Strongly recommended for compliance with data protection regulations",
                    true_label="Yes",
                    false_label="No",
                ),
            ),
            WorkflowParameter(
                task_title="quality-assurance",
                env_variable_name="QA_APPROVAL",
                ui_form=TermsUIForm(
                    type="terms",
                    title="Quality Assurance Certification",
                    description="QA reviewer certification",
                    help="This attestation is logged for audit purposes",
                    terms_text="I certify that I have reviewed the data quality metrics and approve this dataset for analysis according to the study protocol.",
                    default=False,
                    required=True,
                ),
            ),
        ],
        labels=[
            Label(
                key="kaapana-ui.description",
                value="Process clinical trial data with regulatory compliance checks and patient consent verification.",
            ),
            Label(key="kaapana-ui.category", value="clinical-research"),
            Label(key="kaapana-ui.provider", value="dkfz-mic"),
        ],
    ),
    WorkflowCreate(
        title="Classification Workflow",
        definition=DEFINITION,
        workflow_engine="Docker",
        workflow_parameters=PARAMETERS,
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
        workflow_parameters=PARAMETERS,
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
        workflow_parameters=PARAMETERS,
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
        workflow_parameters=PARAMETERS,
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
        workflow_parameters=PARAMETERS,
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

                response = await create_workflow(
                    workflow_create=workflow
                )
                response.raise_for_status()
                created_workflow = Workflow(**response.json())
                print(
                    f"Created generated workflow: {created_workflow.title} (v{created_workflow.version})"
                )

                # randomly create 1-3 additional versions for ~30% of generated workflows
                if randint(1, 1) <= 3:
                    extra_versions = randint(1, 1)
                    for _ in range(extra_versions):
                        # re-create workflow (server should bump version)
                        resp2 = await create_workflow(workflow_create=workflow)
                        resp2.raise_for_status()
                        created2 = Workflow(**resp2.json())
                        print(
                            f"  -> Created extra version: {created2.title} (v{created2.version})"
                        )

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
                        workflow=schemas.WorkflowRef(
                            title=wf_title, version=chosen_version
                        ),
                        labels=[],
                        workflow_parameters=PARAMETERS,
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
        # First try to delete all workflow runs (if DELETE endpoint exists)
        print("\n=== Attempting to Delete All Workflow Runs ===")
        try:
            response = await get_all_workflow_runs()
            response.raise_for_status()
            workflow_runs = response.json()
            for wf_run in workflow_runs:
                run_id = wf_run.get("id")
                if run_id:
                    try:
                        response = await delete_workflow_run(workflow_run_id=run_id)
                        response.raise_for_status()
                        print(f"DELETED WORKFLOW RUN -> ID: {run_id}")
                    except httpx.HTTPStatusError as e:
                        # Check if it's a 405 Method Not Allowed or 404 Not Found
                        if e.response.status_code in [404, 405]:
                            print("WARNING: DELETE endpoint for workflow runs not implemented - skipping workflow runs")
                            break
                        print(f"Failed to delete workflow run {run_id}: {e}")
        except Exception as e:
            print(f"WARNING: Could not delete workflow runs: {e}")
        
        # Then delete all workflows
        print("\n=== Deleting All Workflows ===")
        response = await get_all_workflows()
        response.raise_for_status()
        workflows = [Workflow(**wf) for wf in response.json()]
        for wf in workflows:
            response = await delete_workflow(title=wf.title, version=wf.version)
            response.raise_for_status()
            print(f"DELETED WORKFLOW -> Title: {wf.title}, Version: {wf.version}")
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
