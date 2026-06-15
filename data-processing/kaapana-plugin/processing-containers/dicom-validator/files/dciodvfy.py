import os
import re
import subprocess

from base import ValidationItem, DicomValidatorInterface
from kaapanapy.logger import get_logger

logger = get_logger(__name__)


class DCIodValidator(DicomValidatorInterface):
    def __init__(self) -> None:
        super().__init__()
        # Per-file timeout (seconds) for the dciodvfy subprocess. A single
        # malformed DICOM can otherwise make dciodvfy block indefinitely and
        # hang the whole validation run until the operator's execution_timeout
        # kills the pod. Configurable via DCIODVFY_TIMEOUT.
        self.timeout = int(os.getenv("DCIODVFY_TIMEOUT", "120"))

    @staticmethod
    def process_dciodvfy_output(output: str):
        """
        Process the output from the dciodvfy command.

        Args:
            output (str): The raw output string from the dciodvfy command.

        Returns:
            List[Tuple[str]]: A list of tuples, where each tuple contains parts of an error or warning message.
        """
        lines = output.split("\n")
        outputs = []

        for l in lines:
            if l.strip() == "":
                continue

            splitted = tuple(l.split(" - "))

            outputs.append(splitted)

        return outputs

    @staticmethod
    def get_validataion_item_from_err_tuple(source: tuple, ref: int = -1):
        """
        Extract a ValidationItem from an error tuple.

        Args:
            source (Tuple[str]): A tuple containing parts of an error or warning message.
            ref (int, optional): A reference index used for naming general tags. Defaults to -1.

        Returns:
            Union[ValidationItem, None]: A ValidationItem instance if extraction is successful, otherwise None.
        """
        valid_tag_regex = re.compile(r"<\/|[A-Za-z0-9]*\([0-9]{4},[0-9]{4}\)\[\d\]>")

        def extract_tag(target: str):
            extracted = re.search(r"\([0-9a-fA-F]{4},[0-9a-fA-F]{4}\)", target)
            if extracted:
                return extracted.group(0)
            extracted_wout_brakets = re.search(r"[0-9a-fA-F]{4},[0-9a-fA-F]{4}", target)
            if extracted_wout_brakets:
                return f"({extracted_wout_brakets.group(0)})"

            # print(f"Could not able to extract tag from {target}")
            return ""

        def extract_name(target: str):
            isvalid = re.match(valid_tag_regex, target)
            if not isvalid:
                # print(f'{target} is not a valid tag')
                return ""

            name_extracted = re.search(r"<\/[A-Za-z0-9]+\(", target)
            if name_extracted:
                extract = name_extracted.group(0)
                return extract[2:-1]

            return ""

        def extract_index(target: str):
            isvalid = re.match(valid_tag_regex, target)
            if not isvalid:
                return None

            idx_extracted = re.search(r"\[\d\]", target)
            if idx_extracted:
                extract = idx_extracted.group(0)
                return int(extract[1:-1])

            return None

        if len(source) > 1:
            vtype = source[0]
            tag = extract_tag(source[1])
            if tag == "" and ref != -1:
                tag = f"general-{ref}"
            elif tag == "":
                tag = "general"
            name = extract_name(source[1])
            index = extract_index(source[1])
            message = source[2]
            module = ""
            if len(source) > 3:
                module = source[3]
            return ValidationItem(
                tag,
                vtype,
                message,
                name,
                module,
                index=index,
                # raw=' - '.join(map(str, source)),
            )

        return None

    def validate_dicom(self, dicom_path: str) -> tuple:
        """
        Validate a DICOM file using the dciodvfy tool.

        Args:
            dicom_path (str): The file path of the DICOM file to be validated.

        Returns:
            Tuple[List[ValidationItem], List[ValidationItem]]: Two lists containing error and warning ValidationItems respectively.
        """
        cmd = ["dciodvfy", "-new", dicom_path]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            _, err = process.communicate(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            logger.warning(
                f"dciodvfy timed out after {self.timeout}s validating "
                f"{dicom_path}; skipping this file."
            )
            return [], []
        errs = self.process_dciodvfy_output(err.decode("utf-8"))
        vitems = [
            self.get_validataion_item_from_err_tuple(item, idx)
            for idx, item in enumerate(errs)
            if self.get_validataion_item_from_err_tuple(item)
        ]
        errors, warnings = [], []

        for item in vitems:
            if item.type == "Error":
                errors.append(item)
            else:
                warnings.append(item)

        return errors, warnings
