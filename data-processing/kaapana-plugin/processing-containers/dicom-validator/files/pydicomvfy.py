import re
import logging
from pathlib import Path
from dicom_validator.spec_reader.edition_reader import EditionReader
from dicom_validator.validator.dicom_file_validator import DicomFileValidator

from base import DicomValidator, ValidationItem


class PyDicomValidator(DicomValidator):
    def __init__(
        self,
        dicom_definition_root: str = "/kaapana/dicom-revisions",
        revision: str = "2024a",
        log_level: int = logging.ERROR,
    ) -> None:
        super().__init__()
        self.dicom_definition_root = dicom_definition_root
        self.revision = revision
        self.validator = self._load_validator(log_level)

    def _load_validator(self, log_level: int = logging.DEBUG):
        edition_reader = EditionReader(self.dicom_definition_root)
        # destination = edition_reader.get_revision(self.revision, recreate_json=False, create_json=False)
        destination = Path(self.dicom_definition_root, self.revision)

        json_path = Path(destination, "json")
        dicom_info = EditionReader.load_dicom_info(json_path)

        validator = DicomFileValidator(dicom_info, log_level, force_read=False)
        return validator

    @staticmethod
    def get_validatation_item_form_err_mssg(tag: str, raw_mssg: str, module: str = ""):
        tag_pos = raw_mssg.find(tag.upper())
        if tag_pos != -1:
            cropped_mssg = raw_mssg[tag_pos + len(tag) :]
        else:
            cropped_mssg = raw_mssg[:]

        def extract_name(target: str):
            target = target.strip()
            if target[0] != "(":
                return "", target

            name_extracted = re.search(r"\(([^\(\)]*)\)", target)
            if name_extracted:
                return name_extracted.group(1), name_extracted.group(0)

            return "", target

        tag_name, tag_part = extract_name(cropped_mssg)
        if tag_name:
            cropped_mssg = cropped_mssg.replace(tag_part, "")

        return ValidationItem(
            tag=tag,
            type="Error",
            message=cropped_mssg.strip(),
            name=tag_name,
            module=module,
        )

    def validate_dicom(self, dicom_path: str):
        out = self.validator.validate(dicom_path)
        modules = out[dicom_path]
        errors = []
        warnings = []
        for m in modules:
            item = modules[m]
            for k in item.keys():
                err = self.get_validatation_item_form_err_mssg(item[k][0], k, module=m)
                errors.append(err)

        return errors, warnings
