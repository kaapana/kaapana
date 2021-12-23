import logging
import sys
import os
from .globals import *
from .Datamodel import KaapanaDatamodel
from .Exceptions import DatamodelException

DM = None

def _init():
    global DM

    log = logging.getLogger(__name__)
    log.info("Initalizing datamodel library")
    # s3_compatible_storage_server = os.getenv(S3_STORAGE_SERVER_ENV)
    # if s3_compatible_storage_server:
    #     log.info("Creating default datamodel instance")
    #     DM = KaapanaDatamodel()
        #datamodel = KaapanaDatamodel(s3_compatible_storage_server)
    DM = KaapanaDatamodel()

_init()
#
audit_logger = logging.getLogger('datamodel_audit')
audit_logger.setLevel(logging.INFO)
logger = logging.getLogger('datamodel')
logger.setLevel(logging.DEBUG)
#logger.addHandler(logging.FileHandler("datamodel"))
audit_logger.addHandler(logging.FileHandler("datamodel_audit"))
