"""
Shared test data for unit tests.

This module contains reusable test data that can be imported by multiple test files.
All workflow definitions are centralized here to avoid redundancy.
"""

# ========== LABELS ==========

LABEL_ENVIRONMENT_PROD = {"key": "environment", "value": "production"}
LABEL_ENVIRONMENT_DEV = {"key": "environment", "value": "development"}
LABEL_TEAM = {"key": "team", "value": "data-science"}
LABEL_VERSION = {"key": "version", "value": "v1.0"}
LABEL_PROJECT = {"key": "project", "value": "medical-imaging"}
LABEL_PRIORITY_HIGH = {"key": "priority", "value": "high"}


def create_label_model(label_dict: dict):
    """Helper to create Label model from dict for database operations."""
    from app.models import Label

    return Label(**label_dict)


# ========== WORKFLOW PARAMETERS ==========

PARAM_BOOL_ENABLE_CACHE = {
    "task_title": "preprocessing",
    "env_variable_name": "ENABLE_CACHE",
    "ui_form": {
        "type": "bool",
        "title": "Enable Cache",
        "description": "Whether to enable caching",
        "default": True,
        "required": False,
        "true_label": "Enabled",
        "false_label": "Disabled",
    },
}

PARAM_LIST_ORGAN = {
    "task_title": "segmentation",
    "env_variable_name": "ORGAN",
    "ui_form": {
        "type": "list",
        "title": "Select Organ",
        "description": "Choose the organ to segment",
        "options": ["liver", "kidney", "spleen"],
        "default": "liver",
        "multiselectable": False,
        "required": True,
    },
}

PARAM_INT_THRESHOLD = {
    "task_title": "task1",
    "env_variable_name": "THRESHOLD",
    "ui_form": {
        "type": "int",
        "title": "Threshold",
        "description": "Set threshold value",
        "default": 50,
        "minimum": 0,
        "maximum": 100,
        "required": True,
    },
}

PARAM_FLOAT_ALPHA = {
    "task_title": "task2",
    "env_variable_name": "ALPHA",
    "ui_form": {
        "type": "float",
        "title": "Alpha",
        "description": "Alpha parameter",
        "default": 0.5,
        "minimum": 0.0,
        "maximum": 1.0,
    },
}

PARAM_STR_MODEL_NAME = {
    "task_title": "processing",
    "env_variable_name": "MODEL_NAME",
    "ui_form": {
        "type": "str",
        "title": "Model Name",
        "description": "Name of the model to use",
        "regex_pattern": r"^[a-zA-Z0-9_-]+$",
        "default": "default_model",
        "required": True,
    },
}

# ========== BASE WORKFLOW DEFINITIONS ==========
# These are the canonical workflow definitions used across all tests
# They include 'version' for database operations

WORKFLOW_BASIC = {
    "title": "test-workflow",
    "version": 1,
    "definition": "test_definition",
    "workflow_engine": "dummy",
}

WORKFLOW_WITH_LABELS = {
    "title": "workflow-with-labels",
    "version": 1,
    "definition": "test_def",
    "workflow_engine": "dummy",
    "labels": [LABEL_ENVIRONMENT_PROD, LABEL_TEAM],
}

WORKFLOW_WITH_BOOL_PARAM = {
    "title": "workflow-with-bool-param",
    "version": 1,
    "definition": "test_def",
    "workflow_engine": "dummy",
    "workflow_parameters": [PARAM_BOOL_ENABLE_CACHE],
}

WORKFLOW_WITH_LIST_PARAM = {
    "title": "workflow-with-list-param",
    "version": 1,
    "definition": "test_def",
    "workflow_engine": "dummy",
    "workflow_parameters": [PARAM_LIST_ORGAN],
}

WORKFLOW_WITH_MULTI_PARAMS = {
    "title": "workflow-multi-params",
    "version": 1,
    "definition": "test_def",
    "workflow_engine": "dummy",
    "workflow_parameters": [PARAM_INT_THRESHOLD, PARAM_FLOAT_ALPHA],
}

WORKFLOW_WITH_LABELS_AND_PARAMS = {
    "title": "workflow-labels-and-params",
    "version": 1,
    "definition": "test_def",
    "workflow_engine": "dummy",
    "labels": [LABEL_VERSION, LABEL_PROJECT],
    "workflow_parameters": [PARAM_STR_MODEL_NAME],
}

# Additional workflow definitions for specific tests
WORKFLOW_1 = {"title": "workflow-1", "version": 1, "definition": "def-1", "workflow_engine": "dummy"}
WORKFLOW_2 = {"title": "workflow-2", "version": 1, "definition": "def-2", "workflow_engine": "dummy"}
WORKFLOW_A_V1 = {"title": "workflow-a", "version": 1, "definition": "def-a1", "workflow_engine": "dummy"}
WORKFLOW_A_V2 = {"title": "workflow-a", "version": 2, "definition": "def-a2", "workflow_engine": "dummy"}
WORKFLOW_B_V1 = {"title": "workflow-b", "version": 1, "definition": "def-b1", "workflow_engine": "dummy"}


def create_workflow_variant(base_workflow: dict, **overrides) -> dict:
    """
    Create a variant of a workflow with overrides.
    Useful for creating multiple versions or slight variations.
    """
    workflow = base_workflow.copy()
    workflow.update(overrides)
    return workflow


def remove_version(workflow: dict) -> dict:
    """Remove version field from workflow (for CREATE API tests)."""
    return {k: v for k, v in workflow.items() if k != "version"}


# ========== PARAMETRIZE DATA FOR CREATE TESTS ==========
# Remove 'version' field for CREATE tests (API assigns version automatically)

CREATE_WORKFLOW_TEST_CASES = [
    (remove_version(WORKFLOW_BASIC), "basic"),
    (remove_version(WORKFLOW_WITH_LABELS), "with_labels"),
    (remove_version(WORKFLOW_WITH_BOOL_PARAM), "with_bool_param"),
    (remove_version(WORKFLOW_WITH_LIST_PARAM), "with_list_param"),
    (remove_version(WORKFLOW_WITH_MULTI_PARAMS), "multi_params"),
    (remove_version(WORKFLOW_WITH_LABELS_AND_PARAMS), "labels_and_params"),
]

VALIDATION_ERROR_TEST_CASES = [
    # Missing required fields
    ({"title": "incomplete"}, 422, "missing_definition"),
    ({"definition": "test"}, 422, "missing_title"),
    ({"title": "test", "definition": "test"}, 422, "missing_engine"),
    # Invalid data types
    (
        {"title": "test", "version": "not-an-integer", "definition": "test", "workflow_engine": "dummy"},
        422,
        "invalid_version_type",
    ),
    (
        {"title": 123, "definition": "test", "workflow_engine": "dummy"},
        422,
        "invalid_title_type",
    ),
    (
        {"title": "test", "definition": ["not", "string"], "workflow_engine": "dummy"},
        422,
        "invalid_definition_type",
    ),
]

READ_WORKFLOW_ERROR_TEST_CASES = [
    ("/v1/workflows/non-existent-title", 404, "title_not_found"),
    ("/v1/workflows/non-existent-title/1", 404, "title_version_not_found"),
    ("/v1/workflows/non-existent-title/999", 404, "high_version_not_found"),
    ("/v1/workflows/test/not-an-int", 422, "invalid_version_type"),
]

# ========== READ WORKFLOWS TEST DATA ==========
# Reuse base workflow definitions

READ_WORKFLOWS_TEST_CASES = [
    ([WORKFLOW_1], "single"),
    ([WORKFLOW_1, WORKFLOW_2], "multiple"),
    (
        [
            WORKFLOW_1,
            create_workflow_variant(WORKFLOW_1, version=2, definition="def-2"),
            create_workflow_variant(WORKFLOW_1, version=3, definition="def-3"),
        ],
        "versions",
    ),
    ([WORKFLOW_A_V1, WORKFLOW_A_V2, WORKFLOW_B_V1], "mixed"),
    (
        [
            create_workflow_variant(WORKFLOW_1, title="workflow-labeled-1", labels=[{"key": "env", "value": "dev"}]),
            create_workflow_variant(
                WORKFLOW_2,
                title="workflow-labeled-2",
                labels=[{"key": "team", "value": "backend"}, {"key": "priority", "value": "high"}],
            ),
        ],
        "with_labels",
    ),
    (
        [
            create_workflow_variant(
                WORKFLOW_1,
                title="workflow-params-1",
                workflow_parameters=[
                    {
                        "task_title": "task1",
                        "env_variable_name": "PARAM1",
                        "ui_form": {"type": "bool", "title": "Param 1", "description": "Boolean parameter", "default": True},
                    }
                ],
            ),
            create_workflow_variant(WORKFLOW_2, title="workflow-params-2", workflow_parameters=[PARAM_LIST_ORGAN]),
        ],
        "with_params",
    ),
]

# ========== DELETE WORKFLOW TEST DATA ==========

DELETE_WORKFLOW_TEST_CASES = [
    ("existing-workflow", 1, 204, "successful_delete"),
    ("non-existent", 1, 404, "workflow_not_found"),
    ("existing-workflow", 999, 404, "version_not_found"),
]

# ========== GET WORKFLOW BY TITLE TEST DATA ==========

GET_WORKFLOW_BY_TITLE_TEST_CASES = [
    (
        "single-version-workflow",
        [create_workflow_variant(WORKFLOW_1, title="single-version-workflow")],
        False,  # latest parameter
        1,  # expected count
        "single_version",
    ),
    (
        "multi-version-workflow",
        [
            create_workflow_variant(WORKFLOW_1, title="multi-version-workflow"),
            create_workflow_variant(WORKFLOW_1, title="multi-version-workflow", version=2, definition="def-2"),
            create_workflow_variant(WORKFLOW_1, title="multi-version-workflow", version=3, definition="def-3"),
        ],
        False,
        3,
        "multiple_versions_all",
    ),
    (
        "latest-version-workflow",
        [
            create_workflow_variant(WORKFLOW_1, title="latest-version-workflow"),
            create_workflow_variant(WORKFLOW_1, title="latest-version-workflow", version=2, definition="def-2"),
        ],
        True,
        1,
        "latest_version_only",
    ),
]

# ========== GET WORKFLOW BY TITLE AND VERSION TEST DATA ==========

GET_WORKFLOW_BY_TITLE_VERSION_TEST_CASES = [
    (
        create_workflow_variant(WORKFLOW_1, title="specific-workflow"),
        "specific-workflow",
        1,
        "basic",
    ),
    (WORKFLOW_WITH_LABELS, "workflow-with-labels", 1, "with_labels"),
]
