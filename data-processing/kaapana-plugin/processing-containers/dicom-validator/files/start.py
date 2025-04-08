import ast
import glob
import os
import re
from datetime import datetime

import pydicom
from base import (
    ValidationItem,
    ensure_dir,
    merge_similar_validation_items,
    DicomValidatorInterface,
)
from check_completeness import check_completeness
from dciodvfy import DCIodValidator
from htmlgen import generate_html
from kaapanapy.logger import get_logger
from kaapanapy.settings import OpensearchSettings, OperatorSettings
from kaapanapy.utils import (
    ConfigError,
    is_batch_mode,
    process_batches,
    process_single,
)
from pathlib import Path
from pydicomvfy import PyDicomValidator
from validation_results_to_os import ValdationResultItem, ValidationResult2Meta

logger = get_logger(__name__)


def get_series_description(all_dicoms: list, meta_key: str = "SeriesDescription"):
    desc = "Unnamed Series"
    for dcm in all_dicoms:
        ds = pydicom.dcmread(dcm)
        try:
            elem = ds[meta_key]
        except KeyError:
            print(f"{meta_key} not found for dicoms")
            break
        if elem:
            desc = elem.value
            break

    return desc


def filter_errors_by_tag_whitelist(errors: list, whitelist: list):
    return [e for e in errors if e.tag not in whitelist]


def validate_dicom_tag(rawtag: str):
    """
    Validates if the provided string is a valid DICOM tag.

    This function checks if the given string follows the DICOM tag format,
    which consists of two groups of four hexadecimal digits, separated by a comma
    and enclosed in parentheses (e.g., (0010,0010)).

    Args:
        rawtag (str): The input string representing the DICOM tag to be validated.

    Returns:
        bool: True if the input string is a valid DICOM tag, False otherwise.
    """
    tagpattern = re.compile(r"^\([0-9a-fA-F]{4},[0-9a-fA-F]{4}\)$")
    matched = tagpattern.match(rawtag)
    if matched:
        return True
    return False


def run_dicom_validation(
    operator_in_dir: Path,
    operator_out_dir: Path,
    validator: DicomValidatorInterface,
    workflow_id: str,
    tags_whitelist: list = [],
    exit_on_error: bool = False,
    results_2_meta: ValidationResult2Meta = None,
):
    completeness_items = check_completeness(
        Path(operator_in_dir), Path(operator_out_dir), update_os=True
    )

    logger.info(f"Series Completeness validation items: ")
    logger.info(completeness_items)

    # The processing algorithm
    print(f"Checking {operator_in_dir} for dcm files")
    dcm_files = sorted(
        glob.glob(os.path.join(operator_in_dir, "*.dcm*"), recursive=True)
    )

    if len(dcm_files) == 0:
        return False, f"No dicom file found in {operator_in_dir}"

    logger.info(("Validating Dicom files, starting with: %s" % dcm_files[0]))

    n_valid = 0
    n_fail = 0

    all_errors = {}
    all_warnings = {}
    for dicom_path in dcm_files:
        errs, warns = validator.validate_dicom(dicom_path)
        if len(tags_whitelist) > 0:
            errs = filter_errors_by_tag_whitelist(errs, tags_whitelist)
            warns = filter_errors_by_tag_whitelist(warns, tags_whitelist)
        key = os.path.basename(dicom_path)

        if len(warns) > 0:
            all_warnings[key] = warns
        if len(errs) > 0:
            all_errors[key] = errs
            n_fail += 1
        else:
            n_valid += 1

    errors = merge_similar_validation_items(all_errors)
    warnings = merge_similar_validation_items(all_warnings)
    seriesdsc = get_series_description(dcm_files)
    validation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    attributes = {
        "Series Name": seriesdsc,
        "Validation Algorithm": validator_alg,
        "Run ID": run_id,
        "Workflow ID": workflow_id,
        "Total number of slices": len(dcm_files),
        "Number of Valid / Invalid slices": str(n_valid) + " / " + str(n_fail),
        "Validataion Time": f"{validation_time} CEST",
    }

    if not completeness_items.is_series_complete:
        attributes["Series Complete"] = False
        attributes["Missing instances"] = len(
            completeness_items.missing_instance_numbers
        )

    if results_2_meta:
        n_errors = len(errors.keys())
        n_warnings = len(errors.keys())

        tags_tuple = [
            ValdationResultItem(
                "Errors", "integer", n_errors
            ),  # (key, opensearch datatype, value)
            ValdationResultItem("Warnings", "integer", n_warnings),
            ValdationResultItem("Date", "datetime", validation_time),
        ]

        series_uid = get_series_description(dcm_files, meta_key="SeriesInstanceUID")

        results_2_meta.add_tags_to_opensearch(
            series_uid,
            validation_tags=tags_tuple,
            clear_results=True,
        )

    if len(errors.keys()) > 0 or len(warnings.keys()) > 0:
        htmlout = generate_html(
            title=f"Validation Report for dataset {seriesdsc}",
            attrs=attributes,
            errors=[errors[tag] for tag in errors.keys()],
            warnings=[warnings[tag] for tag in warnings.keys()],
            series_completete_stat=completeness_items,
        )

        with open(os.path.join(operator_out_dir, f"results-{run_id}.html"), "w") as f:
            f.write(htmlout)

        logger.info(
            f"Validation Results file created in {operator_out_dir} with the name results-{run_id}.html"
        )

    if len(errors.keys()) > 0 and exit_on_error:
        raise ValueError(
            f"Dicom Validation Failed. Stopping Executions. Validation Results file created in {operator_out_dir} with the name results-{run_id}.html listing all the errors."
        )

    return True, f"Successfully validated series: {seriesdsc}"


if __name__ == "__main__":
    try:
        # Airflow variables
        operator_settings = OperatorSettings()
        thread_count = int(os.getenv("THREADS", "3"))
        if thread_count is None:
            logger.error("Missing required environment variable: THREADS")
            raise ConfigError("Missing required environment variable: THREADS")

        # Operator settings variables
        run_id = operator_settings.run_id
        workflow_dir = Path(operator_settings.workflow_dir)
        batch_name = operator_settings.batch_name
        operator_in_dir = Path(operator_settings.operator_in_dir)
        operator_out_dir = Path(operator_settings.operator_out_dir)

        if not workflow_dir.exists():
            logger.error(f"{workflow_dir} directory does not exist")
            raise ConfigError(f"{workflow_dir} directory does not exist")

        batch_dir = workflow_dir / batch_name
        if not batch_dir.exists():
            logger.error(f"{batch_dir} directory does not exist")
            raise ConfigError(f"{batch_dir} directory does not exist")
    except Exception as e:
        logger.critical(f"Configuration error: {e}")
        raise SystemExit(1)  # Gracefully exit the program

    # load all the Operator specific variables from the environment
    workflow_id = os.environ.get("WORKFLOW_ID", "")
    validator_alg = os.environ.get("VALIDATOR_ALGORITHM", "").lower()
    exit_on_error = os.environ.get("EXIT_ON_ERROR", "False")
    exit_on_error = True if exit_on_error.lower() == "true" else False

    # extract and validate tags whitelist
    tags_whitelist = os.environ.get("TAGS_WHITELIST", "[]")
    tags_whitelist = ast.literal_eval(tags_whitelist)
    tags_whitelist = [t for t in tags_whitelist if validate_dicom_tag(t)]
    dicom_defintion_root = "/kaapana/dicom-revisions"

    logger.info(
        "All required directories and environment variables are validated successfully."
    )

    logger.info("Starting thumbnail generation")

    logger.info(f"thread_count: {thread_count}")
    logger.info(f"workflow_dir: {workflow_dir}")
    logger.info(f"batch_name: {batch_name}")
    logger.info(f"operator_in_dir: {operator_in_dir}")
    logger.info(f"operator_out_dir: {operator_out_dir}")

    batch_mode = is_batch_mode(workflow_dir=workflow_dir, batch_name=batch_name)

    if validator_alg == "pydicomvalidator" or validator_alg == "dicom-validator":
        validator = PyDicomValidator(dicom_definition_root=dicom_defintion_root)
    else:
        validator = DCIodValidator()

    results_2_meta = ValidationResult2Meta()

    if batch_mode:
        process_batches(
            # Required
            batch_dir=Path(batch_dir),
            operator_in_dir=Path(operator_in_dir),
            operator_out_dir=Path(operator_out_dir),
            processing_function=run_dicom_validation,
            thread_count=thread_count,
            validator=validator,
            workflow_id=workflow_id,
            tags_whitelist=tags_whitelist,
            exit_on_error=exit_on_error,
            results_2_meta=results_2_meta,
        )
    else:
        process_single(
            # Required
            base_dir=Path(workflow_dir),
            operator_in_dir=Path(operator_in_dir),
            operator_out_dir=Path(operator_out_dir),
            processing_function=run_dicom_validation,
            thread_count=thread_count,
            validator=validator,
            workflow_id=workflow_id,
            tags_whitelist=tags_whitelist,
            exit_on_error=exit_on_error,
            results_2_meta=results_2_meta,
        )
