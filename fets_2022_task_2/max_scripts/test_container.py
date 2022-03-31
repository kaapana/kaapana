"""
This script can be executed by participants to test their container locally before submitting it
"""

import argparse
import json
import logging
from pathlib import Path
from subprocess import TimeoutExpired
import tempfile


def check_prediction_folder(pred_path: Path, data_path: Path):
    missing_cases = []

    subjects = list(data_path.iterdir())
    predictions = list(pred_path.iterdir())
    for case in subjects:
        match_found = -1
        for i, pred in enumerate(predictions):
            if pred.name == f"{case.name}_seg.nii.gz":
                match_found = i
                break
        if match_found >= 0:
            predictions.pop(match_found)
        else:
            missing_cases.append(case.name)
    if len(predictions) > 0:
        logging.error(f"The output folder contains files/folders that do not comply with the naming convention:\n{[str(el) for el in predictions]}")
        return False, missing_cases
    if len(missing_cases) > 0:
        logging.error(f"{len(missing_cases)} cases did not have a prediction:\n{missing_cases}")
    return True, missing_cases


if __name__ == "__main__":
    # This import works only if this is executed as a script
    from run_submission import run_container
    from metric_evaluation import evaluate_regions

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "sif_file", type=str,
        help="Name of the container file you want to test. Should have the format 'teamXYZ.sif'"
    )
    parser.add_argument(
        "-i",
        "--input_dir", required=True, type=str,
        help="Input data lies here. Make sure it has the correct folder structure!",
    )
    parser.add_argument(
        "-o", "--output_dir", required=False, type=str, help="Folder where the output/predictions will be written to"
    )
    parser.add_argument(
        "-l",
        "--label_dir", required=False, type=str, default="",
        help="Labels for the input data lie here. Make sure it contains one file per case with name <case-id>_seg.nii.gz",
    )
    parser.add_argument(
        "--timeout", default=180, required=False, type=int,
        help="Time budget PER CASE in seconds. Evaluation will be stopped after the total timeout of timeout * n_cases."
    )
    parser.add_argument(
        "--log_file", default='test.log', required=False, type=str,
        help="Path where logs should be stored."
    )

    args = parser.parse_args()

    TIME_PER_CASE = args.timeout   # seconds
    sif_file = Path(args.sif_file)
    input_dir = Path(args.input_dir)

    logging.basicConfig(handlers=[logging.FileHandler(args.log_file), logging.StreamHandler()],
                    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    tmp_dir = None
    if args.output_dir is None:
        # will be deleted at the end of the script
        tmp_dir = tempfile.TemporaryDirectory()
        output_dir = Path(tmp_dir.name)
    else:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)

    logging.info("Testing FeTS singularity image...")
    logging.info("================================")
    included_subjects = [x.name for x in input_dir.iterdir() if x.is_dir()]   # all subjects
    # This runs the container in the same way it is done in the testing phase
    timeout = False
    try:
        runtime = run_container(
                sif_file,
                in_dir=input_dir,
                out_dir=output_dir,
                subject_list=included_subjects,
                timeout_case=TIME_PER_CASE
            )
    except TimeoutExpired:
        runtime = TIME_PER_CASE * len(included_subjects)
        timeout = True
    logging.info("================================")
    if timeout:
        logging.warning(f"Container execution was aborted after {runtime} s because the specified timeout was reached. "
                        "Depending on your hardware setup, this could be problematic or not.")
    else:
        logging.info(f"Finished container execution. Runtime: {runtime:.1f} seconds")

    # check output
    folder_ok, missing_cases = check_prediction_folder(output_dir, input_dir)
    if folder_ok:
        if len(args.label_dir) > 0:
            logging.info("Computing metrics...")
            logging.warning("Note that these metric values are just for sanity checks and the implementation "
                            "for the federated evaluation will be based on https://cbica.github.io/CaPTk/BraTS_Metrics.html.")
            results = evaluate_regions(output_dir, args.label_dir)
            logging.info(f"{json.dumps(results, indent=4)}")
            with open(output_dir / 'metrics.json', 'w') as f:
                json.dump(results, f, indent=2)
        else:
            logging.info("Won't compute metrics because no label folder was passed...")    
    else:
        logging.error("Output folder test not passed. Please check the error messages in the logs.")

    if tmp_dir is not None:
        logging.info("Cleaning up temporary output folder...")
        tmp_dir.cleanup()

    logging.info("Done. Please check any error messages or warnings in the log!")