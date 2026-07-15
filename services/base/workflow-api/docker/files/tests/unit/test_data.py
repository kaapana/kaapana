"""Shared test data for unit tests."""

# ========== LABELS ==========

LABEL_ENVIRONMENT_PROD = {"key": "environment", "value": "production"}
LABEL_ENVIRONMENT_DEV = {"key": "environment", "value": "development"}
LABEL_TEAM = {"key": "team", "value": "data-science"}
LABEL_VERSION = {"key": "version", "value": "v1.0"}
LABEL_PROJECT = {"key": "project", "value": "medical-imaging"}
LABEL_PRIORITY_HIGH = {"key": "priority", "value": "high"}


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

# ========== WORKFLOW CREATE PAYLOADS ==========

WORKFLOW_BASIC = {
    "title": "test-workflow",
    "definition": "test_definition",
    "workflow_engine": "dummy",
}

WORKFLOW_WITH_LABELS = {
    "title": "workflow-with-labels",
    "definition": "test_def",
    "workflow_engine": "dummy",
    "labels": [LABEL_ENVIRONMENT_PROD, LABEL_TEAM],
}

WORKFLOW_WITH_BOOL_PARAM = {
    "title": "workflow-with-bool-param",
    "definition": "test_def",
    "workflow_engine": "dummy",
    "workflow_parameters": [PARAM_BOOL_ENABLE_CACHE],
}

WORKFLOW_WITH_LIST_PARAM = {
    "title": "workflow-with-list-param",
    "definition": "test_def",
    "workflow_engine": "dummy",
    "workflow_parameters": [PARAM_LIST_ORGAN],
}

WORKFLOW_WITH_MULTI_PARAMS = {
    "title": "workflow-multi-params",
    "definition": "test_def",
    "workflow_engine": "dummy",
    "workflow_parameters": [PARAM_INT_THRESHOLD, PARAM_FLOAT_ALPHA],
}

WORKFLOW_WITH_LABELS_AND_PARAMS = {
    "title": "workflow-labels-and-params",
    "definition": "test_def",
    "workflow_engine": "dummy",
    "labels": [LABEL_VERSION, LABEL_PROJECT],
    "workflow_parameters": [PARAM_STR_MODEL_NAME],
}


CREATE_WORKFLOW_TEST_CASES = [
    (WORKFLOW_BASIC, "basic"),
    (WORKFLOW_WITH_LABELS, "with_labels"),
    (WORKFLOW_WITH_BOOL_PARAM, "with_bool_param"),
    (WORKFLOW_WITH_LIST_PARAM, "with_list_param"),
    (WORKFLOW_WITH_MULTI_PARAMS, "multi_params"),
    (WORKFLOW_WITH_LABELS_AND_PARAMS, "labels_and_params"),
]

VALIDATION_ERROR_TEST_CASES = [
    # Missing required fields
    ({"title": "incomplete"}, 422, "missing_definition"),
    ({"definition": "test"}, 422, "missing_title"),
    ({"title": "test", "definition": "test"}, 422, "missing_engine"),
    # Unknown field — Pydantic extra=forbid rejects
    (
        {
            "title": "test",
            "increment": "not-an-integer",
            "definition": "test",
            "workflow_engine": "dummy",
        },
        422,
        "increment_not_settable_on_create",
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
