from datetime import datetime
from enum import Enum
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkflowRunStatus(str, Enum):
    CREATED = "Created"  # Created in Workflow-API DB, not yet picked up by engine
    PENDING = "Pending"  # Picked up by engine, waiting to be scheduled
    SCHEDULED = "Scheduled"  # Scheduled by engine, waiting to run
    RUNNING = "Running"  # Currently running
    ERROR = "Error"  # Execution failed
    COMPLETED = "Completed"  # Successfully completed
    CANCELED = "Canceled"  # Execution canceled


class TaskRunStatus(str, Enum):
    CREATED = "Created"
    PENDING = "Pending"
    SCHEDULED = "Scheduled"
    RUNNING = "Running"
    ERROR = "Error"
    COMPLETED = "Completed"
    SKIPPED = "Skipped"


class Label(BaseModel):
    key: str
    value: str

    model_config = ConfigDict(from_attributes=True)


#####################################
######## WORKFLOWCONFIG #############
#####################################


class BaseUIForm(BaseModel):
    """
    Base class for all UI form definitions.

    Each UI form represents a configuration field that can be rendered in a frontend client to collect user input.

    Common attributes such as `title`, `description`, and `default` are inherited by all form types.

    Attributes:
        type (str): Type discriminator used to determine the UI form variant.
        title (str): Short title or display name for this input field.
        description (str): Detailed description of the purpose of this field.
        help (Optional[str]): Additional help text, tooltip, or usage hint.
        required (bool): Whether this field is required in the form. Defaults to False.
        default (Optional[Any]): Default value for this field, if applicable.
    """

    type: str = Field(..., description="Type of the UI form element.")
    title: str = Field(..., description="Display title for the input field.")
    description: str = Field(..., description="Detailed description of this parameter.")
    help: Optional[str] = Field(
        None, description="Additional help or usage information."
    )
    required: Optional[bool] = Field(
        False, description="Whether the field is required."
    )
    default: Optional[Any] = Field(None, description="Default value for the field.")


class BooleanUIForm(BaseUIForm):
    """
    Boolean input form element.

    Represents a simple true/false toggle, rendered in the UI as a
    checkbox, switch, or similar control.

    Attributes:
        type (Literal["bool"]): Discriminator identifying this as a boolean field.
        true_label (Optional[str]): Optional label to display when the value is `True`.
        false_label (Optional[str]): Optional label to display when the value is `False`.
    """

    type: Literal["bool"] = "bool"
    true_label: Optional[str] = Field(
        None,
        description="Optional label to display when the value is True (e.g. 'Enabled').",
    )
    false_label: Optional[str] = Field(
        None,
        description="Optional label to display when the value is False (e.g. 'Disabled').",
    )


class IntegerUIForm(BaseUIForm):
    """
    Integer input form element.

    Allows the user to input an integer number, optionally constrained by minimum and maximum bounds.

    Attributes:
        type (Literal["int"]): Discriminator identifying this as an integer field.
        minimum (Optional[int]): Minimum allowed value for the integer input.
        maximum (Optional[int]): Maximum allowed value for the integer input.
    """

    type: Literal["int"] = "int"
    minimum: Optional[int] = Field(None, description="Minimum allowed integer value.")
    maximum: Optional[int] = Field(None, description="Maximum allowed integer value.")


class FloatUIForm(BaseUIForm):
    """
    Float input form element.

    Allows the user to input a float number, optionally constrained by minimum and maximum bounds.

    Attributes:
        type (Literal["float"]): Discriminator identifying this as an float field.
        minimum (Optional[float]): Minimum allowed value for the float input.
        maximum (Optional[float]): Maximum allowed value for the float input.
    """

    type: Literal["float"] = "float"
    minimum: Optional[float] = Field(None, description="Minimum allowed float value.")
    maximum: Optional[float] = Field(None, description="Maximum allowed float value.")


class ListUIForm(BaseUIForm):
    """
    List or dropdown input form element.

    Allows the user to select one or multiple values from a
    predefined list of options.

    Attributes:
        type (Literal["list"]): Discriminator identifying this as a list field.
        options (Optional[List[str]]): Available selectable options.
        multiselectable (bool): Whether multiple options can be selected. Defaults to False.
    """

    type: Literal["list"] = "list"
    options: Optional[List[str]] = Field(
        None,
        description=(
            "List of available options for selection. "
            "Example: ['dice_score', 'surface_dice', 'hausdorff_distance']"
        ),
    )
    multiselectable: bool = Field(False, description="Allow multiple selections.")


class StringUIForm(BaseUIForm):
    """
    String or text input form element.

    Allows the user to enter free-form text, optionally validated
    against a regular expression pattern.

    Attributes:
        type (Literal["str"]): Discriminator identifying this as a string field.
        regex_pattern (str): Regular expression pattern used to validate the input value.
    """

    type: Literal["str"] = "str"
    regex_pattern: str = Field(
        ..., description="Regex pattern for validating the string input."
    )


class DatasetUIForm(BaseUIForm):
    """
    Dataset selection form element.

    Allows the user to select a dataset that exists in the Kaapana backend.

    Attributes:
        type (Literal["dataset"]): Discriminator identifying this as a dataset selector.
    """

    type: Literal["dataset"] = "dataset"


class DataEntitiesUIForm(BaseUIForm):
    """
    Data entity selection form element.

    Displays a list of data entities retrieved from the Data API
    based on a provided query. Supports pagination and result limits.

    Attributes:
        type (Literal["data_entity"]): Discriminator identifying this as a data entity selector.
        query (str): Query string used to fetch matching entities from the Data API.
        limit (int): Maximum number of data entities to display.
        pagination (bool): Whether to enable pagination for long lists.
    """

    type: Literal["data_entity"] = "data_entity"
    query: str = Field(
        ..., description="Query string to fetch data entities from the Data API."
    )
    limit: int = Field(..., description="Maximum number of results to return.")
    pagination: bool = Field(
        ..., description="Enable pagination in the result display."
    )


class FileUIForm(BaseUIForm):
    """
    File upload form element.

    Allows the user to upload a file from their local filesystem.

    Attributes:
        type (Literal["file"]): Discriminator identifying this as a file upload field.
        accept (str | None): Comma-separated list of accepted file types/extensions (e.g., ".json,.yaml").
        multiple (bool): Whether to allow multiple file uploads.
    """

    type: Literal["file"] = "file"
    accept: str | None = Field(
        default=None, description="Accepted file types (e.g., '.json,.yaml,.txt')."
    )
    multiple: bool = Field(
        default=False, description="Whether to allow multiple file uploads."
    )


class TermsUIForm(BaseUIForm):
    """
    Terms and conditions acceptance form element.

    Displays terms and conditions text that the user must accept before proceeding.
    Always rendered as a checkbox that must be checked.

    Attributes:
        type (Literal["terms"]): Discriminator identifying this as a terms acceptance field.
        terms_text (str): The text of the terms and conditions to display.
    """

    type: Literal["terms"] = "terms"
    terms_text: str = Field(
        ..., description="The terms and conditions text that the user must accept."
    )


UIForm = Union[
    BooleanUIForm,
    StringUIForm,
    IntegerUIForm,
    FloatUIForm,
    ListUIForm,
    DatasetUIForm,
    DataEntitiesUIForm,
    FileUIForm,
    TermsUIForm,
]


class WorkflowParameter(BaseModel):
    """
    A parameter that can be configured by users when starting a WorkflowRun.
    Parameters correspond to an environment variable of a specific task in a WorkflowRun.

    :param task_title: Title of the task in the Workflow.
    :param env_variable_name: Name of the environment variable.
    :param ui_form: Configurations used by clients to render a UI component for configuring the parameter.


    **Example:**

    WorkflowParameter(
        task_title="segment_organ",
        env_variable_name="ORGAN",
        ui_form=UIForm(
            type="list",
            options=["liver", "kidney"],
            default="liver",
            multiselectable=False,
            required=True,
            title="organ",
            description="Select the organ to be segmented",
        ),
    )
    """

    task_title: str
    env_variable_name: str
    ui_form: UIForm = Field(..., discriminator="type")

    model_config = ConfigDict(from_attributes=True)


#####################################
############## WORKFLOW #############
#####################################


class WorkflowBase(BaseModel):
    title: str
    definition: str
    workflow_engine: str
    workflow_parameters: Optional[List[WorkflowParameter]] = None
    labels: List[Label] = []

    @field_validator("labels")
    @classmethod
    def validate_unique_labels(cls, labels: List[Label]) -> List[Label]:
        """Ensure labels don't contain duplicates based on key-value pairs."""
        seen = set()
        for label in labels:
            label_tuple = (label.key, label.value)
            if label_tuple in seen:
                raise ValueError(
                    f"Duplicate label found: key='{label.key}', value='{label.value}'. "
                    "Each label must have a unique key-value combination."
                )
            seen.add(label_tuple)
        return labels


class WorkflowCreate(WorkflowBase):
    model_config = ConfigDict(extra="forbid")


class Workflow(WorkflowBase):
    id: int
    version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


#####################################
############## TASKS ################
#####################################


class TaskBase(BaseModel):
    display_name: Optional[str] = None
    title: str
    type: Optional[str] = None


class TaskCreate(TaskBase):
    downstream_task_titles: List[str] = []


class Task(TaskBase):
    id: int
    workflow_id: int
    downstream_task_ids: List[int] = []

    model_config = ConfigDict(from_attributes=True)


#####################################
############# TASK RUN ##############
#####################################


class TaskRunBase(BaseModel):
    task_title: str  # The title of the task this run belongs to in the engine
    lifecycle_status: TaskRunStatus
    external_id: str  # The unique ID of the task run in the engine (the API does not know about it when this is passed the first time, therefore we also have the task title for linking)


class TaskRunCreate(TaskRunBase):
    workflow_run_id: int
    task_id: int  # The title of the task this run belongs to


class TaskRun(TaskRunBase):
    id: int
    task_id: int  # The title of the task this run belongs to
    workflow_run_id: int

    model_config = ConfigDict(from_attributes=True)


class TaskRunUpdate(TaskRunBase):
    pass


#####################################
############## WORKFLOWRUN ##########
#####################################


class WorkflowRef(BaseModel):
    """Lightweight reference to a Workflow for embedding in WorkflowRun."""

    title: str
    version: int

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunBase(BaseModel):
    workflow: WorkflowRef
    labels: List[Label] = []
    workflow_parameters: Optional[List[WorkflowParameter]] = None


class WorkflowRunCreate(WorkflowRunBase):
    pass


class WorkflowRun(WorkflowRunBase):
    id: int
    external_id: str | None
    created_at: datetime
    lifecycle_status: WorkflowRunStatus
    workflow: WorkflowRef
    task_runs: List[TaskRun] = Field(default_factory=list)
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunUpdate(BaseModel):
    # external_id is optional for updates that only change lifecycle_status
    external_id: Optional[str] = None
    lifecycle_status: Optional[WorkflowRunStatus] = None
