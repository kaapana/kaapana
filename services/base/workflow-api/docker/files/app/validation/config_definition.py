"""  - Dataselections : e.g. dataset, minio-path, DataEntity
                    |---- task_identifier e.g. InputOperator / get-input
                    |---- Env-VariableName e.g.  channel1
                    |---- query e.g. DICOM_SEG via Data API
                    |---- kaapana_backend (v1) datasets
        - WorkflowParameters: e.g. delete entire study (str, list, dict)
                    |---- task_identifier e.g. InputOperator / get-input
                    |---- Env-VariableName e.g. DELETE_COMPLETE_STUDY (str)
                    |---- title
                    |---- choices e.g. enums  [ "dice_score",  "surface_dice","average_surface_distance", "hausdorff_distance"]
                    |---- type e.g. array, string, boolean, int
                    |---- default e.g. 1
                    |---- description e.g. "The tag must exist in all test segmentations, and must not exist in ground truth data"
                    |---- required 
                    |---- "minimum" and "maximum" for int e.g. 1-999

        - 
        - Description:  Additional UI Information

"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class WorkflowParameterUI(BaseModel):
    title: str
    options: Optional[List[str]] = None  # Renamed from `choices`
    type: str  # e.g. "array", "string", "bool", "int"
    default: Optional[Any] = None
    description: Optional[str] = None
    required: Optional[bool] = False
    minimum: Optional[int] = None
    maximum: Optional[int] = None


class WorkflowParameter(BaseModel):
    task_identifier: str
    env_variable_name: str
    ui_params: WorkflowParameterUI

class KaapanaBackendSelection(BaseModel):
    identifiers: List[str]
    dataset_name: Optional[str] = None

class DataSelection(BaseModel):
    task_identifier: str
    env_variable_name: str
    query: Optional[str] = None
    kaapana_backend: Optional[KaapanaBackendSelection] = None


class ConfigDefinition(BaseModel):
    dataselections: Optional[List[DataSelection]] = None
    workflow_parameters: Optional[List[WorkflowParameter]] = None
    description: Optional[str] = None


    class Config:
        extra = "forbid"  # unknown keys cause validation error