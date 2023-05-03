import functools
from pathlib import Path

from kaapana.operators.HelperMinio import HelperMinio


def properties_filter(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        default_json_schema = func(*args, **kwargs)
        if len(args) > 0:
            filter_keys = args[0]
        else:
            filter_keys = kwargs.get("filter_keys", [])
        if filter_keys:
            filtered_json_schema = {}
            for k in filter_keys:
                filtered_json_schema[k] = default_json_schema[k]
            return filtered_json_schema
        return default_json_schema

    return wrapper


@properties_filter
def properties_workflow_execution(filter_keys: list = None):
    return {
        "single_execution": {
            "type": "boolean",
            "title": "Single execution",
            "description": "Whether your report is execute in single mode or not",
            "default": False,
            "readOnly": False,
            "required": True
        }
    }


@properties_filter
def properties_dataset_form(filter_keys: list = None):
    return {
        "dataset_name": {
            "type": "string",
            "title": "Dataset name (size)",
            "oneOf": [],
            "required": True
        },
        "dataset_limit": {
            "type": "integer",
            "title": "Limit dataset size",
            "description": "Limit dataset to this many cases."
        }
    }


def schema_dataset_form(filter_keys: list = None):
    return {
        "data_form": {
            "type": "object",
            "properties": {**properties_dataset_form(filter_keys)}
        }
    }


def schema_minio_form(select_options="files",
                      blacklist_directory_endings: tuple = (),
                      whitelist_object_endings: tuple = ()):
    if select_options not in ["both", "files", "folders"]:
        raise Exception(
            "select_options has to be either both, files or folders")
    try:
        objects = HelperMinio.list_objects(HelperMinio.minioClient,
                                           "uploads", recursive=True,
                                           )
        object_names = [obj.object_name for obj in objects]
        filtered_minio_objects = [object_name for object_name in object_names if
                                  object_name.endswith(
                                      whitelist_object_endings)]

        filtered_minio_directories = []
        for object_name in object_names:
            object_directory = str(Path(object_name).parents[0])
            if not object_directory.endswith(blacklist_directory_endings):
                filtered_minio_directories.append(
                    str(Path(object_name).parents[0]))
    except Exception as e:
        filtered_minio_directories = ["Something does not work :/"]
        filtered_minio_objects = ["Something does not work :/"]
    if select_options == "both":
        return {
            "data_form": {
                "type": "object",
                "title": "Select file or folder from Minio",
                "description": "The uplods/itk directory in Minio is crawled for zip files and folders",
                "properties": {
                    "bucket_name": {
                        "title": "Bucket name",
                        "description": "Bucket name from MinIO",
                        "type": "string",
                        "default": "uploads",
                        "readOnly": True
                    }
                },
                "oneOf": [
                    {
                        "title": "Search for files",
                        "properties": {
                            "identifier": {
                                "type": "string",
                                "const": "files"
                            },
                            "action_files": {
                                "title": "Objects from bucket",
                                "description": "Relative paths to object in Bucket",
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": filtered_minio_objects
                                },
                                "readOnly": False
                            }
                        }
                    },
                    {
                        "title": "Search for folders",
                        "properties": {
                            "identifier": {
                                "type": "string",
                                "const": "folders"
                            },
                            "action_operator_dirs": {
                                "title": "Directories",
                                "description": "Directory from bucket",
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": list(
                                        set(filtered_minio_directories))
                                },
                                "readOnly": False
                            }
                        }
                    }
                ]
            }
        }
    elif select_options == "files":
        return {
            "data_form": {
                "type": "object",
                "properties": {
                    "bucket_name": {
                        "title": "Bucket name",
                        "description": "Bucket name from MinIO",
                        "type": "string",
                        "default": "uploads",
                        "readOnly": True
                    },
                    "action_files": {
                        "title": "Objects from bucket",
                        "description": "Relative paths to object in Bucket",
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": filtered_minio_objects
                        },
                        "readOnly": False
                    }
                }
            }
        }
    elif select_options == "folders":
        return {
            "data_form": {
                "type": "object",
                "properties": {
                    "bucket_name": {
                        "title": "Bucket name",
                        "description": "Bucket name from MinIO",
                        "type": "string",
                        "default": "uploads",
                        "readOnly": True
                    },
                    "action_operator_dirs": {
                        "title": "Directories",
                        "description": "Directory from bucket",
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": list(set(filtered_minio_directories))
                        },
                        "readOnly": False
                    }
                }
            }
        }


@properties_filter
def properties_external_federated_form(filter_keys: list = None):
    return {
        "federated_bucket": {
            "type": "string",
            "title": "Federated bucket",
            "description": "Bucket to which the files should be saved to",
            "readOnly": True
        },
        "federated_dir": {
            "type": "string",
            "title": "Federated directory",
            "description": "Directory to which the files should be saved to",
            "readOnly": True
        },
        "federated_operators": {
            "type": "array",
            "title": "Operators for which the results should be saved",
            "items": {
                "type": "string"
            },
            "readOnly": True
        },
        "skip_operators": {
            "type": "array",
            "title": "Operators that should not be executed",
            "items": {
                "type": "string"
            },
            "readOnly": True
        },
        "federated_round": {
            "type": "integer",
            "title": "Federated round",
            "readOnly": True
        },
        "federated_total_rounds": {
            "type": "integer",
            "title": "Federated total rounds"
        }
    }
