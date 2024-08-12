#!/usr/bin/env python3
# -*- coding: utf-8; mode: python; indent-tabs-mode: nil; -*-

import os
from kaapanapy.helper import get_opensearch_client, get_project_user_access_token
from kaapanapy.logger import get_logger
from opensearchpy.exceptions import TransportError
import requests
import traceback
import json
import time

tries = 0
# TODO https://discuss.elastic.co/t/reloading-the-index-field-list-automatically/116687
# https://<domain>/meta/api/index_patterns/_fields_for_wildcard?pattern=meta-index&meta_fields=%5B%22_source%22%2C%22_id%22%2C%22_type%22%2C%22_index%22%2C%22_score%22%5D

logger = get_logger(__name__)


def import_dashboards():
    global dashboards_url, export_ndjson_path, tries
    logger.info(f"Importing dashboards from {export_ndjson_path} ...")
    time.sleep(5)

    files = {
        "file": open(export_ndjson_path, "rb"),
    }
    if tries > 5:
        logger.error(f"Too many tries: {tries} -> abort.")
        exit(1)

    try:
        access_token = get_project_user_access_token()
        logger.debug(f"{access_token=}")
        response = requests.post(
            f"{dashboards_url}/api/saved_objects/_import",
            headers={
                "osd-xsrf": "true",
                "Authorization": f"Bearer {access_token}",
            },
            files=files,
        )
        logger.debug(response.text)
        logger.debug(response.status_code)
        response.raise_for_status()

        if response.status_code == 200:
            logger.info(f"# {export_ndjson_path}: OK!")

        elif response.text == "OpenSearch Dashboards server is not ready yet":
            logger.info("OpenSearch Dashboards server is not ready yet")
            logger.info("waiting ...")
            tries += 1
            time.sleep(10)
            logger.info("restart import_dashboards() ...")
            import_dashboards()
            return

        else:
            logger.error(f"Could not import dashboard: {export_ndjson_path}")
            logger.error(response.text)
            exit(1)
    except Exception as e:
        logger.warning(traceback.format_exc())
        logger.warning(f"Could not import dashboard: {export_ndjson_path} -> Exception")
        tries += 1
        logger.warning("waiting ...")
        time.sleep(10)
        logger.warning("restart import_dashboards() ...")
        import_dashboards()

    logger.info("Dashboard import successful!")


def set_ohif_template():
    global dashboards_url, domain, https_port, index
    logger.info(f"Creating OHIF template ...")
    index_pattern = {
        "attributes": {
            "title": "{}".format(index),
            "fieldFormatMap": '{"0020000D StudyInstanceUID_keyword.keyword":{"id":"url","params":{"urlTemplate":"https://'
            + domain
            + ":"
            + https_port
            + '/ohif/viewer?StudyInstanceUIDs={{value}}","labelTemplate":"{{value}}"}}}',
        }
    }
    try:
        access_token = get_project_user_access_token()
        response = requests.put(
            f"{dashboards_url}/api/saved_objects/index-pattern/{index}?overwrite=true",
            data=json.dumps(index_pattern),
            verify=False,
            headers={
                "osd-xsrf": "true",
                "Authorization": f"Bearer {access_token}",
            },
        )
        logger.info(f"response_code: {response.status_code}")
        if response.status_code == 200:
            logger.info("OHIF-template: OK!")
        else:
            logger.error("OHIF-template: Error!")
            logger.error(response.text)
            logger.error(response.content)
            exit(1)

    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error("OHIF-template: Error!")
        exit(1)


def create_index():
    global os_client, index
    logger.info(f"Creating index: {index} ...")
    index_name = index
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

    def _create_index(index_name, index_body):
        try:
            response = os_client.indices.create(index_name, body=index_body)
            return response
        except TransportError as e:
            if str(e.error) == "resource_already_exists_exception":
                logger.warning("# Index already exists ...")
                return True
            else:
                logger.warning("Retry ...")
                return False
        except Exception as e:
            logger.error("Unknown issue while creating the META index ...")
            raise e

    counter = 0
    max_retries = 60
    while not _create_index(index_name, index_body) and counter <= max_retries:
        time.sleep(1)
        counter += 1

    if counter > max_retries:
        logger.error("Max retries exceeded:  {counter=} > {max_retries=}")
        logger.error("Index not successfully created!")
        exit(1)

    logger.info("Index created successfully!")


logger.info("Started init-container")

if __name__ == "__main__":
    logger.info("# Provisioning...")

    init_dashboards = (
        True if os.getenv("INIT_DASHBOARDS", False).lower() == "true" else False
    )
    init_os = True if os.getenv("INIT_OPENSEARCH", False).lower() == "true" else False

    # stack_version = os.getenv('STACKVERSION', '6.8.12')
    domain = os.getenv("DOMAIN", None)
    https_port = os.getenv("HTTPS_PORT", None)
    index = os.getenv("INDEX", None)
    os_host = os.getenv("OPENSEARCH_HOST", None)
    os_port = os.getenv("OPENSEARCH_POST", None)
    dashboards_url = os.getenv("DASHBOARDS_URL", None)
    export_ndjson_path = os.getenv("EXPORT_NDJSON", None)

    logger.info("Configuration:")
    logger.info(f"domain:          {domain}")
    logger.info(f"https_port:      {https_port}")
    logger.info(f"index:           {index}")
    logger.info(f"os_host:         {os_host}")
    logger.info(f"os_port:         {os_port}")
    logger.info(f"dashboards_url:  {dashboards_url}")
    logger.info(f"init_dashboards: {init_dashboards}")
    logger.info(f"init_os:         {init_os}")
    logger.info(f"export_ndjson_path: {export_ndjson_path}")

    if domain is None:
        logger.error("DOMAIN env not set -> exiting..")
        exit(1)

    os_client = get_opensearch_client()

    if init_os:
        logger.info("Initializing OpenSearch indices...")
        create_index()
        logger.info("Done.")

    if init_dashboards:
        logger.info("Initializing Dashboards...")
        import_dashboards()
        set_ohif_template()
        logger.info("Done.")

    logger.info("All done - End of init-container.")
