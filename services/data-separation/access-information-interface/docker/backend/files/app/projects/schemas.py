from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator
import re


class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreateProject(OrmBaseModel):
    external_id: Optional[str] = None
    name: str
    description: str

    @field_validator("name", mode="before")
    @classmethod
    def validate_project_name(cls, v):
        from app.projects import minio, opensearch, kubehelm

        """
        Validate if the project name satisfies naming rules for buckets in minio, namespaces in kubernetes and indices in opensearch.
        """

        s3_bucket = f"project-{v}"
        valid_bucket_name = minio.is_valid_minio_bucket_name(s3_bucket)
        if not valid_bucket_name:
            raise AssertionError(
                f"Invalid MINIO bucket name {s3_bucket}. {minio.is_valid_minio_bucket_name.__doc__}"
            )

        opensearch_index = f"project_{v}"
        valid_opensearch_index_name = opensearch.is_valid_opensearch_index_name(
            opensearch_index
        )
        if not valid_opensearch_index_name:
            raise AssertionError(
                f"Invalid OpenSearch Index name {opensearch_index}. {opensearch.is_valid_opensearch_index_name.__doc__}"
            )

        kubernetes_namespace = f"project-{v}"
        valid_kubernetes_namespace = kubehelm.is_valid_kubernetes_namespace(
            kubernetes_namespace
        )
        if not valid_kubernetes_namespace:
            raise AssertionError(
                f"Invalid Kubernetes Namespace {kubernetes_namespace}. {kubehelm.is_valid_kubernetes_namespace.__doc__}"
            )

        # AE title can only be uppercase, project name converted to uppercase
        # for validation
        valid_ae_title = is_valid_dicom_ae_title(v.upper())
        if not valid_ae_title:
            raise AssertionError(
                f"Invalid AE TITLE {v.upper()}. {is_valid_dicom_ae_title.__doc__}"
            )
        return v


def is_valid_dicom_ae_title(ae_title: str) -> bool:
    """
    https://pydicom.github.io/pynetdicom/dev/user/ae.html
    AE titles must meet the conditions of a DICOM data element with a Value Representation of AE:
    * Leading and trailing spaces (hex 0x20) are non-significant.
    * Maximum 16 characters (once non-significant characters are removed).
    * Valid characters belong to the DICOM Default Character Repertoire, which is the basic G0 Set
        of the ISO/IEC 646:1991 (ASCII) standard excluding backslash (\ - hex 0x5C) and all control
        characters (such as '\n').
    * An AE title made entirely of spaces is not allowed.
    """
    # Strip leading and trailing spaces (non-significant)
    stripped_title = ae_title.strip()

    # Check length after stripping spaces
    if not (1 <= len(stripped_title) <= 16):
        return False

    # Ensure the title is not entirely spaces
    if not stripped_title:
        return False

    # Define the allowed characters in the DICOM Default Character Repertoire, excluding backslash
    # This includes uppercase letters, digits, and certain punctuation characters
    valid_pattern = r"^[A-Z0-9 _!\"#$%&\'()*+,-./:;<=>?@^_`{|}~]*$"

    # Check if the stripped title only contains valid characters
    return bool(re.fullmatch(valid_pattern, stripped_title))


class Project(OrmBaseModel):
    id: int
    external_id: Optional[str] = None
    name: str
    description: str
    kubernetes_namespace: str
    s3_bucket: str
    opensearch_index: str


class CreateRight(OrmBaseModel):
    claim_key: str
    claim_value: str
    name: str
    description: str


class Right(OrmBaseModel):
    id: int
    name: str
    description: str
    claim_key: str
    claim_value: str


class CreateRole(OrmBaseModel):
    name: str
    description: str


class Role(OrmBaseModel):
    id: int
    description: str
    name: str


class Software(OrmBaseModel):
    software_uuid: str
