import json
import logging

auth_role_mapping_path = "/app/auth_role_mapping.json"
global auth_role_mapping_dict, logger

def load_auth_config():
    global auth_role_mapping_dict, logger
    
    with open(auth_role_mapping_path) as f:
        auth_role_mapping_dict = json.load(f)

    logger.info(json.dumps(auth_role_mapping_dict, indent=4))


logger = logging.getLogger(__name__)
load_auth_config()