from enum import Enum

class DataType(Enum):
    DICOM = 0
    RAW = 1
    NRRD = 2
    NIFTI = 3
    ## ...


class StorageLocation(Enum):
    LOCAL_PACS = 0
    LOCAL_OBJECT_STORE = 1
    REMOTE_PACS = 2
    REMOTE_OBJECT_STORE = 3