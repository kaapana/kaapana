import logging
import sys
import os
from .globals import *
from .DatamodelB import KaapanaDatamodelB
from .Exceptions import DatamodelException

# DM = None
#
# def _init():
#     global DM
#
#     log = logging.getLogger(__name__)
#     log.info("Initalizing datamodel library")
#     # s3_compatible_storage_server = os.getenv(S3_STORAGE_SERVER_ENV)
#     # if s3_compatible_storage_server:
#     #     log.info("Creating default datamodel instance")
#     #     DM = KaapanaDatamodel()
#         #datamodel = KaapanaDatamodel(s3_compatible_storage_server)
#     DM = KaapanaDatamodel()
#
# _init()
#
DM = KaapanaDatamodelB()
logging_file = os.path.join("log", "datamodel.log")
if not os.path.isdir("log"):
    os.mkdir("log")

logging.basicConfig(filename=logging_file, format='%(asctime)s (%(levelname)s) %(message)s', level=logging.DEBUG,
                    datefmt='%d.%m.%Y %H:%M:%S')
streamHandler = logging.StreamHandler(sys.stdout)
streamHandler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(streamHandler)