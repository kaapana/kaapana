import body_organ_analysis as boa
from pathlib import Path
import sys
import logging
logger = logging.getLogger(__name__)

if __name__=="__main__":
    INPUT_FOLDER=sys.argv[1]
    SEGMENTATION_FODLER=sys.argv[2]
    try:
        boa.store_dicoms(input_folder=Path(INPUT_FOLDER), segmentation_folder=Path(SEGMENTATION_FODLER))
    except KeyError as e:
        if e.args[0] == 'UPLOAD_USER':
            logger.debug("We do not upload dicoms to a PACS.")
        logger.debug(str(e))