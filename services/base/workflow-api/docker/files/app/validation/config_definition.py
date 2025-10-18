from typing import List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class WorkflowParameterUI(BaseModel):
    options: Optional[List[str]] = (
        None  # [ "dice_score",  "surface_dice","average_surface_distance", "hausdorff_distance"]
    )
    type: str  # e.g. "array", "string", "bool", "int"
    default: Optional[Any] = None
    minimum: Optional[int] = None
    maximum: Optional[int] = None


class DataSelectionUI(BaseModel):
    query: Optional[str] = None  # DICOM_SEG via Data API
    kaapana_backend_identifiers: List[str]
    kaapana_backend_dataset_name: Optional[str] = None


class WorkflowParameter(BaseModel):
    title: str
    # "The tag must exist in all test segmentations, and must not exist in ground truth data"
    description: Optional[str] = None
    task_title: str  # get-input
    # DELETE_COMPLETE_STUDY (str)
    env_variable_name: str
    required: Optional[bool] = False
    ui_params: WorkflowParameterUI | DataSelectionUI


class ConfigDefinition(BaseModel):
    workflow_parameters: Optional[List[WorkflowParameter]] = None
    description: Optional[str] = None

    class Config:
        extra = "forbid"  # unknown keys cause validation error
