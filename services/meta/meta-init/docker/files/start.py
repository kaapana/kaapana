import requests
import os
from opensearchpy.exceptions import TransportError
from kaapanapy.helper import get_opensearch_client, get_project_user_access_token
from kaapanapy.logger import get_logger
import time

logger = get_logger(__name__)

index_template_body = {
    "index_patterns": ["project_*"],
    "template": {
        "settings": {
            "index.mapping.total_fields.limit": "6000",
            "index.number_of_shards": "4",
            "index.number_of_replicas": "0",
            "index.max_docvalue_fields_search": "150",
        },
        "mappings": {
            "numeric_detection": False,
            "dynamic": "true",
            "dynamic_templates": [
                {
                    "check_integer": {
                        "match_pattern": "regex",
                        "mapping": {"type": "long"},
                        "match": "^.*_integer.*$",
                    }
                },
                {
                    "check_float": {
                        "match_pattern": "regex",
                        "mapping": {"type": "float"},
                        "match": "^.*_float.*$",
                    }
                },
                {
                    "check_double": {
                        "match_pattern": "regex",
                        "mapping": {"type": "double"},
                        "match": "^.*_double.*$",
                    }
                },
                {
                    "check_datetime": {
                        "match_pattern": "regex",
                        "mapping": {
                            "format": "yyyy-MM-dd HH:mm:ss.SSSSSS",
                            "type": "date",
                        },
                        "match": "^.*_datetime.*$",
                    }
                },
                {
                    "check_date": {
                        "match_pattern": "regex",
                        "mapping": {"format": "yyyy-MM-dd", "type": "date"},
                        "match": "^.*_date.*$",
                    }
                },
                {
                    "check_time": {
                        "match_pattern": "regex",
                        "mapping": {"format": "HH:mm:ss.SSSSSS", "type": "date"},
                        "match": "^.*_time.*$",
                    }
                },
                {
                    "check_timestamp": {
                        "match_pattern": "regex",
                        "mapping": {
                            "format": "yyyy-MM-dd HH:mm:ss.SSSSSS",
                            "type": "date",
                        },
                        "match": "^.*timestamp.*$",
                    }
                },
                {
                    "check_object": {
                        "match_pattern": "regex",
                        "mapping": {"type": "object"},
                        "match": "^.*_object.*$",
                    }
                },
                {
                    "check_boolean": {
                        "match_pattern": "regex",
                        "mapping": {"type": "boolean"},
                        "match": "^.*_boolean.*$",
                    }
                },
                {
                    "check_array": {
                        "match_pattern": "regex",
                        "mapping": {"type": "array"},
                        "match": "^.*_array.*$",
                    }
                },
            ],
            "date_detection": False,
            "properties": {},
        },
    },
    "composed_of": [],
    "priority": "0",
    "_meta": {"flow": "simple"},
    # "name": "project_index_template",
}

index_body = {
    "settings": {
        "index": {
            "number_of_replicas": 0,
            "number_of_shards": 4,
            "mapping.total_fields.limit": 6000,
            "max_docvalue_fields_search": 150,
        }
    },
    "mappings": {
        "dynamic": "true",
        "date_detection": "false",
        "numeric_detection": "false",
        "dynamic_templates": [
            {
                "check_integer": {
                    "match_pattern": "regex",
                    "match": "^.*_integer.*$",
                    "mapping": {"type": "long"},
                }
            },
            {
                "check_float": {
                    "match_pattern": "regex",
                    "match": "^.*_float.*$",
                    "mapping": {"type": "float"},
                }
            },
            {
                "check_double": {
                    "match_pattern": "regex",
                    "match": "^.*_double.*$",
                    "mapping": {"type": "double"},
                }
            },
            {
                "check_datetime": {
                    "match_pattern": "regex",
                    "match": "^.*_datetime.*$",
                    "mapping": {
                        "type": "date",
                        "format": "yyyy-MM-dd HH:mm:ss.SSSSSS",
                    },
                }
            },
            {
                "check_date": {
                    "match_pattern": "regex",
                    "match": "^.*_date.*$",
                    "mapping": {"type": "date", "format": "yyyy-MM-dd"},
                }
            },
            {
                "check_time": {
                    "match_pattern": "regex",
                    "match": "^.*_time.*$",
                    "mapping": {"type": "date", "format": "HH:mm:ss.SSSSSS"},
                }
            },
            {
                "check_timestamp": {
                    "match_pattern": "regex",
                    "match": "^.*timestamp.*$",
                    "mapping": {
                        "type": "date",
                        "format": "yyyy-MM-dd HH:mm:ss.SSSSSS",
                    },
                }
            },
            {
                "check_object": {
                    "match_pattern": "regex",
                    "match": "^.*_object.*$",
                    "mapping": {"type": "object"},
                }
            },
            {
                "check_boolean": {
                    "match_pattern": "regex",
                    "match": "^.*_boolean.*$",
                    "mapping": {"type": "boolean"},
                }
            },
            {
                "check_array": {
                    "match_pattern": "regex",
                    "match": "^.*_array.*$",
                    "mapping": {"type": "array"},
                }
            },
        ],
    },
}


def import_saved_objects(file_path, access_token):
    DASHBOARDS_URL = os.getenv("DASHBOARDS_URL")
    files = {
        "file": open(file_path, "rb"),
    }
    response = requests.post(
        f"{DASHBOARDS_URL}/api/saved_objects/_import",
        headers={
            "osd-xsrf": "true",
            "Authorization": f"Bearer {access_token}",
        },
        files=files,
    )
    response.raise_for_status()


def replace_hostname_and_port_in_index_pattern(file_path, hostname, https_port):
    """
    Replace the placeholders for hostname and https_port in the ndjson file with the values for the current deployment.
    """
    import re

    hostname_pattern = r"HOSTNAME"
    port_pattern = r"HTTPS_PORT"

    with open(file=file_path, mode="r") as f:
        data = f.read()
        replaced_hostname = re.sub(hostname_pattern, hostname, data)
        replaced_port_and_hostname = re.sub(port_pattern, https_port, replaced_hostname)

    with open(file=file_path, mode="w") as f:
        f.write(replaced_port_and_hostname)


if __name__ == "__main__":
    logger.info("Start initilazing opensearch")
    HOSTNAME = os.getenv("DOMAIN", None)
    HTTPS_PORT = os.getenv("HTTPS_PORT", None)
    os_client = get_opensearch_client()

    ### Create the index template
    successfull = False
    tries = 0
    logger.info("Create index template")
    while not successfull and tries < 60:
        try:
            os_client.indices.put_index_template(
                name="project_", body=index_template_body
            )
            successfull = True
        except TransportError as e:
            if str(e.error) == "resource_already_exists_exception":
                logger.warning("Index template already exists ...")
                successfull = True
                break
            else:
                logger.warning(str(e))
                logger.warning("Retry ...")
                tries += 1
                time.sleep(5)
    if not successfull and tries >= 60:
        raise Exception("Error, when creating index template")

    ### Create default project_init that is necessary in order to create the index_pattern
    logger.info("Create initial index")
    successfull = False
    tries = 0
    while not successfull and tries < 60:
        try:
            os_client.indices.create(index="project_init")
            successfull = True
        except TransportError as e:
            if str(e.error) == "resource_already_exists_exception":
                logger.warning("Index already exists ...")
                successfull = True
                break
            else:
                logger.warning(str(e))
                logger.warning("Retry ...")
                tries += 1
                time.sleep(5)
    if not successfull and tries >= 60:
        raise Exception("Error, when creating index")

    ### Set hostname and https_port in the index pattern file
    replace_hostname_and_port_in_index_pattern(
        "project_index_pattern.ndjson", HOSTNAME, HTTPS_PORT
    )

    ### Wait for dashboard to be available
    logger.info("Wait for dashboard to be available.")
    DASHBOARDS_URL = os.getenv("DASHBOARDS_URL")
    dashboard_available = False
    tries = 0
    while not dashboard_available and tries < 60:
        try:
            r = requests.get(DASHBOARDS_URL)
            r.raise_for_status()
            dashboard_available = True
        except Exception as e:
            tries += 1
            time.sleep(5)
            logger.warning(str(e))
    if not dashboard_available and tries >= 60:
        raise Exception("Dashboard url was not accessable!")

    ### Import files to dashboard via saved_objects API
    files_to_import = [
        "configs.ndjson",
        "project_index_pattern.ndjson",
        "visualizations.ndjson",
        "dashboards.ndjson",
    ]
    access_token = get_project_user_access_token()
    for file in files_to_import:
        logger.info(f"Import object from {file}")
        import_saved_objects(file_path=file, access_token=access_token)
