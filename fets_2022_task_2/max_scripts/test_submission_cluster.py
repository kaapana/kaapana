"""
This script should be executed on the cluster node.

What is done here?
- look for submission details in all_submissions.json (synced from workstation)
- download container to temporary location (e.g. /ssd? But do I really want to download from the cluster node?)
- runs container test as in scripts/test_container.py
- create end.txt if succesfully run
- send an email with the results to the submitting user
- cleanup
"""

import argparse
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

import pandas as pd


# For resolving import issues 
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))


def main(args):
    """
    Rationale behind raising exceptions and setting status to "failed":
    - If the container fails, times out or produces the wrong output, set to failed and report error to participants.
    - If it's not possible to download the container: raise exception (no way to continue)
    - All other cases: my fault, raise exception and investigate
    """
    subm_id = args.submission_id
    time_per_case = args.timeout   # seconds
    send_email = not args.no_mail
    
    # Paths (on cluster!)
    curl_config = '/home/m167k/gitlab_token'   # gitlab API token is inside
    base_path = Path(args.base_path)
    data_path = Path(args.data_path)
    label_path = Path(args.label_path)
    tmp_pred_dir = Path("/ssd/m167k") / os.getenv("LSB_JOBID") / "fets_predictions"   # will be deleted after job is done
    tmp_pred_dir.mkdir(exist_ok=True)
    subm_dir = base_path / str(subm_id)
    if subm_dir.exists():
        # to avoid results from previous runs affecting the latest one
        files_to_delete = list(Path(subm_dir).glob('*.json')) + list(Path(subm_dir).glob('*.txt'))
        for p in files_to_delete:
            p.unlink()
    subm_dir.mkdir(exist_ok=True)
    sif_file = subm_dir / f"{subm_id}.sif"
    
    # submission details
    subm_df =  pd.read_json(base_path / 'all_submissions.json', orient='index')
    subm_dict = subm_df.loc[subm_df.id == subm_id].squeeze()   # keep series for serialization
    with open(subm_dir / 'submission.json', 'w') as f:
        subm_dict.to_json(f, indent=2, date_format='iso')
    subm_dict = subm_dict.to_dict()

    log_path = subm_dir / 'run.log'
    container_log_path = subm_dir / 'container.log'
    logging.basicConfig(handlers=[logging.FileHandler(log_path), logging.StreamHandler()],
                        level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.info("========================")
    logging.info("STARTING SUBMISSION TEST")
    logging.info("========================")

    test_successful = True
    if not sif_file.exists():
        logging.info("Download submission container...")
        download_file(sif_file, curl_config, url=subm_dict['url'], log_file=log_path, raise_status=True)
        # Quick check of file size
        if sif_file.stat().st_size != subm_dict['file_size']:
            raise RuntimeError("File size of the sif-file does not match the expected size. Probably download problem.")

    logging.info("Testing FeTS singularity image...")
    logging.info("================================")
    included_subjects = [x.name for x in data_path.iterdir() if x.is_dir()]   # all subjects
    # This runs the container in the same way it is done in the testing phase
    timeout = False
    try:
        runtime = run_container(
                sif_file,
                in_dir=data_path,
                out_dir=tmp_pred_dir,
                subject_list=included_subjects,
                timeout_case=time_per_case,
                log_file=container_log_path
            )
    except subprocess.TimeoutExpired as e:
        test_successful = False
        runtime = e.timeout
        timeout = True
    except Exception:
        test_successful = False
        logging.error(traceback.format_exc())
        runtime = None
    logging.info("================================")

    # delete excess files in prediction folder here (all but the segmentations)
    accepted_filenames = [f"{subj}_seg.nii.gz" for subj in included_subjects]
    logging.info("Cleaning up output directory...")
    for out_path in tmp_pred_dir.iterdir():
        if out_path.is_dir():
            logging.warning(f"Deleting directory in output folder: {out_path.name}")
            shutil.rmtree(out_path)
        elif out_path.name not in accepted_filenames:
            logging.warning(f"Deleting file in output folder which does follow naming convention: {out_path.name}")
            out_path.unlink()
    # cleanup (delete container file)
    if not args.keep_sif:
        sif_file.unlink()

    if set(accepted_filenames) != set([p.name for p in tmp_pred_dir.iterdir()]):
        logging.error("Could not find a prediction for all cases. This may disqualify this submission for the final evaluation!")
        test_successful = False

    logging.info("Computing metrics...")
    metrics = evaluate_regions(tmp_pred_dir, label_path)
    logging.debug(f"{json.dumps(metrics, indent=4)}")
    with open(subm_dir / 'metrics.json', 'w') as f:
        json.dump(metrics, f)
    with open(subm_dir / 'time.json', 'w') as f:
        json.dump({'runtime [s]': runtime}, f)

    if send_email:
        send_mail(subm_dict, metrics, runtime, timeout, log_file=container_log_path)

    logging.info("Done.")
    if test_successful:
        fname = 'success.txt'
    else:
        fname = 'fail.txt'
    with open(subm_dir / fname, 'w') as f:
        f.write('dummy')


if __name__ == "__main__":
    # made accessible by modifying PATH (see top of file)
    # from scripts.run_submission import run_container
    from scripts.metric_evaluation import evaluate_regions
    from test_submission_federated import download_file, run_container
    from internal.send_submission_email import send_mail

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "submission_id", type=int,
        help="Submission id to test. It should be present in the json file synced to the cluster."
    )
    parser.add_argument(
        "--timeout", default=200, required=False, type=int,
        help="Time budget PER CASE in seconds. Evaluation will be stopped after the total timeout of timeout * n_cases."
    )
    parser.add_argument(
        "--keep_sif", action='store_true', required=False,
        help="Whether to keep the sif-file saved in the submission folder or delete it after the experiment."
    )
    parser.add_argument(
        "--base_path", default='/home/m167k/my_checkpoint_dir/fets_challenge/submissions', type=str, required=False,
        help="Path to submission directory."
    )
    parser.add_argument(
        "--data_path", default='/home/m167k/my_data_dir/fets_challenge/toy_images', type=str, required=False,
        help="Path to data for test run."
    )
    parser.add_argument(
        "--label_path", default='/home/m167k/my_data_dir/fets_challenge/toy_labels', type=str, required=False,
        help="Path to labels for test run."
    )
    parser.add_argument(
        '--no_mail', action='store_true', required=False,
        help="Send no email to user."
    )
    main(parser.parse_args())