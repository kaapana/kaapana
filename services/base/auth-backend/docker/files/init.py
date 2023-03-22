import json
import os
import logging

global auth_role_mapping_dict, error_page
auth_role_mapping_path = "/kaapana/app/auth_role_mapping.json"
error_page_path = "/kaapana/app/403.html"

logger = logging.getLogger("gunicorn.access")

def load_error_page():
    global error_page
    with open(error_page_path, "r", encoding='utf-8') as f:
        error_page= f.read()

def load_auth_config():
    global auth_role_mapping_dict

    if not os.path.exists(auth_role_mapping_path):
        logger.error("")
        logger.error("")
        logger.error("")
        logger.error("Auth-config file not found!")
        logger.error(f"Path: {auth_role_mapping_path}")
        logger.error("")
        logger.error("")
        logger.error("")
        exit(1)

    with open(auth_role_mapping_path) as f:
        auth_role_mapping_dict = json.load(f)

    logger.warn("Auth-config:")
    logger.warn("")
    logger.warn(json.dumps(auth_role_mapping_dict, indent=4))
    logger.warn("")

load_auth_config()
load_error_page()
