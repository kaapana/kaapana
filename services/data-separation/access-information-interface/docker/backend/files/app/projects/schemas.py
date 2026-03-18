import re
from typing import Optional
from uuid import UUID

from app.config import PLATFORM_PREFIX
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreateProject(OrmBaseModel):
    external_id: Optional[str] = None
    name: str
    description: str
    default: bool = False


class UpdateProject(OrmBaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    external_id: Optional[str] = None


def is_valid_dicom_ae_title(ae_title: str) -> bool:
    r"""
    https://pydicom.github.io/pynetdicom/dev/user/ae.html
    AE titles must meet the conditions of a DICOM data element with a Value Representation of AE:
    * Leading and trailing spaces (hex 0x20) are non-significant.
    * Maximum 16 characters (once non-significant characters are removed).
    * Valid characters belong to the DICOM Default Character Repertoire, which is the basic G0 Set
        of the ISO/IEC 646:1991 (ASCII) standard excluding backslash (\\ - hex 0x5C) and all control
        characters (such as '\n').
    * An AE title made entirely of spaces is not allowed.
    """
    # Strip leading and trailing spaces (non-significant)
    stripped_title = ae_title.strip()

    # Check length after stripping spaces
    if not (1 <= len(stripped_title) <= 16):
        return False
    if not stripped_title:
        return False

    # Define the allowed characters in the DICOM Default Character Repertoire, excluding backslash
    # This includes uppercase letters, digits, and certain punctuation characters
    valid_pattern = r"^[A-Z0-9 _!\"#$%&\'()*+,-./:;<=>?@^_`{|}~]*$"

    # Check if the stripped title only contains valid characters
    return bool(re.fullmatch(valid_pattern, stripped_title))


class Project(OrmBaseModel):
    """
    id                          = immutable UUID
    |- short_id                 = id.hex[:8]
        |- kubernetes_namespace = "{PLATFORM_PREFIX}-project-{short_id}"
        |- s3_bucket            = "project-{short_id}"
        |- opensearch_index     = "project_{short_id}"
    """

    id: UUID
    external_id: Optional[str] = None
    name: str
    int_id: Optional[int] = None
    description: str
    is_archived: bool = False
    multiinstallable_whitelist: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def short_id(self) -> str:
        """
        8-char lowercase hex prefix of the project id.
        """
        if (
            self.name == "admin"
        ):  # exception for admin project since it is required in multiple places in the codebase as a default fallback project
            return "admin"
        return self.id.hex[:8]

    @computed_field  # type: ignore[misc]
    @property
    def kubernetes_namespace(self) -> str:
        return f"{PLATFORM_PREFIX}-project-{self.short_id}"

    @computed_field  # type: ignore[misc]
    @property
    def s3_bucket(self) -> str:
        return f"project-{self.short_id}"

    @computed_field  # type: ignore[misc]
    @property
    def opensearch_index(self) -> str:
        return f"project_{self.short_id}"

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v):
        """
        Validate if the name satisfies the AE title naming rules in DICOM standard.
        """

        # AE title can only be uppercase, project name converted to uppercase
        # for validation
        valid_ae_title = is_valid_dicom_ae_title(v.upper())
        if not valid_ae_title:
            raise AssertionError(
                f"Invalid AE TITLE {v.upper()}. {is_valid_dicom_ae_title.__doc__}"
            )
        return v
    


class UpdateMultiinstallableWhitelist(OrmBaseModel):
    app_names: list[str] = Field(default_factory=list)



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
