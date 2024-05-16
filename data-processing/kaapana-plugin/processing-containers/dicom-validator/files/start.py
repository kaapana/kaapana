import os
import glob
from datetime import datetime
import pydicom

from base import ValidationItem, merge_similar_validation_items, ensure_dir
from pydicomvfy import PyDicomValidator
from dciodvfy import DCIodValidator
from htmlgen import generate_html


def get_series_description(all_dicoms: list):
    desc = ""
    for dcm in all_dicoms:
        ds = pydicom.dcmread(dcm)
        elem = ds["SeriesDescription"]
        if elem:
            desc = elem.value
            break

    return desc


if __name__ == "__main__":
    # From the template
    batch_folders = sorted(
        [
            f
            for f in glob.glob(
                os.path.join(
                    "/", os.environ["WORKFLOW_DIR"], os.environ["BATCH_NAME"], "*"
                )
            )
        ]
    )

    run_id = os.environ["RUN_ID"]
    validator_alg = os.environ.get("VALIDATOR_ALGORITHM", "").lower()
    exit_on_error = os.environ.get("EXIT_ON_ERROR", "False")
    exit_on_error = True if exit_on_error.lower() == "true" else False

    dicom_defintion_root = "/kaapana/dicom-revisions"

    if validator_alg == "pydicomvalidator" or validator_alg == "dicom-validator":
        validator = PyDicomValidator(dicom_definition_root=dicom_defintion_root)
    else:
        validator = DCIodValidator()

    for batch_element_dir in batch_folders:
        element_input_dir = os.path.join(
            batch_element_dir, os.environ["OPERATOR_IN_DIR"]
        )
        element_output_dir = os.path.join(
            batch_element_dir, os.environ["OPERATOR_OUT_DIR"]
        )
        ensure_dir(element_output_dir)

        # The processing algorithm
        print(f"Checking {element_input_dir} for dcm files")
        dcm_files = sorted(
            glob.glob(os.path.join(element_input_dir, "*.dcm*"), recursive=True)
        )

        if len(dcm_files) == 0:
            print("No dicom file found!")
            exit(1)
        else:
            print(("Validating Dicom files, starting with: %s" % dcm_files[0]))

            n_valid = 0
            n_fail = 0

            all_errors = {}
            all_warnings = {}
            for dicom_path in dcm_files:
                errors, warns = validator.validate_dicom(dicom_path)
                key = os.path.basename(dicom_path)
                if len(warns) > 0:
                    all_warnings[key] = warns
                if len(errors) > 0:
                    all_errors[key] = errors
                    n_fail += 1
                else:
                    n_valid += 1

            errors = merge_similar_validation_items(all_errors)
            warnings = merge_similar_validation_items(all_warnings)
            attributes = {
                "Series Name": get_series_description(dcm_files),
                "Validation Algorithm": validator_alg,
                "Run id": run_id,
                "Total Dicoms": len(dcm_files),
                "Number of Valid Dicoms": str(n_valid),
                "Number of Failed Dicoms": str(n_fail),
                "Validataion Time": f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')} CEST",
            }

            if len(errors.keys()) > 0 or len(warnings.keys()) > 0:
                htmlout = generate_html(
                    title=f"Error Report for dataset {get_series_description(dcm_files)}",
                    attrs=attributes,
                    errors=[errors[tag] for tag in errors.keys()],
                    warnings=[warnings[tag] for tag in warnings.keys()],
                )

                with open(
                    os.path.join(element_output_dir, f"errors-{run_id}.html"), "w"
                ) as f:
                    f.write(htmlout)

                print(
                    f"Error file created in {element_output_dir} with the name errors-{run_id}.html"
                )

            if len(errors.keys()) > 0 and exit_on_error:
                raise ValueError(
                    f"Dicom Validation Failed. Stopping Executions. Error file created in {element_output_dir} with the name errors-{run_id}.html listing all the errors."
                )
