"""
This should be run at the FeTS node!
"""

import argparse
import csv
import hashlib as hash
import json
import logging
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time
import traceback
from typing import List


class MissingData(Exception):
    def __init__(self, message, found_cases, expected_cases):
        self.message = message
        self.found_cases = found_cases
        self.expected_cases = expected_cases
        super().__init__(self.message)

    def __str__(self):
        return f'Found {self.found_cases} but expected {self.expected_cases} -> {self.message}'


EXIT_STATUS = {
    'success': 'SUCCESS',
    'error': 'ERROR',
    'timeout': 'TIMEOUT',
}


def download_file(target_file: Path, config_path: Path, url=None, log_file: Path=None, raise_status=False):
    # Error handling: I write the stdout of curl to the log file (added http_code), but do not raise an error here if 
    # the http code indicates it. If the server gives an error response, I will notice it in the container check.
    if url:
        logging.info(f"Downloading file {url.split('/')[-1]}...")

    if url is None:
        # url should be in config then
        curl_cmd = f"curl --config {config_path} --output {target_file}" + ' -w "%{http_code}"'
    else:
        curl_cmd = f"curl --config {config_path} --output {target_file} \"{url}\" " + ' -w "%{http_code}"'
    logging.info(curl_cmd)
    start_time = time.monotonic()
    result = subprocess.run(
        shlex.split(curl_cmd),
        check=True,
        stdout=subprocess.PIPE,
        stderr=None,   # curl sends the progress meter here
        )

    logging.info(f"Finished download in {time.monotonic() - start_time:.1f} seconds")
    if raise_status:
        status_code = int(result.stdout.decode('UTF-8').split('\n')[-1])
        if status_code >= 400:
            with open(target_file) as ftarget:
                logging.error(ftarget.read())
            raise RuntimeError(f"curl returned status code {status_code}")
    if log_file:
        with open(log_file, 'a') as flog:
            flog.write(result.stdout.decode('UTF-8'))
    return target_file


def compute_sha256(path, blocksize=65536):
    # blocksize = how many bytes of the file you want to open at a time
    checksum = hash.sha256()
    with open(path, 'rb') as sif:
        file_buffer = sif.read(blocksize)
        while len(file_buffer) > 0:
            checksum.update(file_buffer)
            file_buffer = sif.read(blocksize)
            
    return checksum.hexdigest()


def run_container(sif: Path, in_dir: Path, out_dir: Path, subject_list: List[str], timeout_case: float, log_file=None):
    # These are defined here because they're independent of the user input
    container_in_dir = Path("/data")
    container_out_dir = Path("/out_dir")

    # build singularity bind mount paths (to include only test case images without segmentation)
    # this will result in a very long bind path, unfortunately.
    bind_str = ""
    num_cases = 0
    for case in in_dir.iterdir():
        if case.is_dir() and case.name in subject_list:
            subject_id = case.name
            t1_path = case / f"{subject_id}_brain_t1.nii.gz"
            t1c_path = case / f"{subject_id}_brain_t1ce.nii.gz"
            t2_path = case / f"{subject_id}_brain_t2.nii.gz"
            fl_path = case / f"{subject_id}_brain_flair.nii.gz"

            t1_path_container = container_in_dir / subject_id / f"{subject_id}_brain_t1.nii.gz"
            t1c_path_container = container_in_dir / subject_id / f"{subject_id}_brain_t1ce.nii.gz"
            t2_path_container = container_in_dir / subject_id / f"{subject_id}_brain_t2.nii.gz"
            fl_path_container = container_in_dir / subject_id / f"{subject_id}_brain_flair.nii.gz"

            # check if files exist
            missing_files = []
            if not t1_path.exists():
                missing_files.append(t1_path.name)
            if not t1c_path.exists():
                if (case / f"{subject_id}_brain_t1gd.nii.gz").exists():
                    t1c_path = case / f"{subject_id}_brain_t1gd.nii.gz"   # container path stays the same
                else:
                    missing_files.append(t1c_path.name)
            if not t2_path.exists():
                missing_files.append(t2_path.name)
            if not fl_path.exists():
                if (case / f"{subject_id}_brain_fl.nii.gz").exists():
                    fl_path = case / f"{subject_id}_brain_fl.nii.gz"   # container path stays the same
                else:
                    missing_files.append(fl_path.name)

            if len(missing_files) == 0:
                bind_str += (
                    f"{t1_path}:{t1_path_container}:ro,"
                    f"{t1c_path}:{t1c_path_container}:ro,"
                    f"{t2_path}:{t2_path_container}:ro,"
                    f"{fl_path}:{fl_path_container}:ro,"
                )
                num_cases += 1
            else:
                logging.error(
                    f"For case {case.name}, some files were missing: {', '.join(missing_files)}. "
                    f"Skipping this case..."
                )
        
    assert "_seg.nii.gz" not in bind_str, "Container should not have access to segmentation files!"

    if num_cases != len(subject_list):
        raise MissingData("Not all cases passed in the subject list were found. Check data directory and split file!",
                          num_cases, len(subject_list))
    
    bind_str += f"{out_dir}:/{container_out_dir}:rw"
    logging.debug(f"The bind path string is in total {len(bind_str)} characters long.")
    os.environ["SINGULARITY_BINDPATH"] = bind_str

    singularity_str = (
        f"singularity run -C --writable-tmpfs --net --network=none --nv"
        f" {sif} -i {container_in_dir} -o {container_out_dir}"
    )
    logging.info("Running container with the command:")    
    logging.info(singularity_str)
    f = None
    if log_file:
        f = open(log_file, 'a')
    start_time = time.monotonic()
    subprocess.run(
        shlex.split(singularity_str),
        timeout=timeout_case * num_cases,
        check=True,
        stdout=f,
        stderr=None if f is None else subprocess.STDOUT
    )
    end_time = time.monotonic()
    if f:
        f.close()

    logging.info(f"Execution time of the container (predicted {num_cases} cases): {end_time - start_time:0.2f} s")
    return end_time - start_time


def main(args):
    data_path = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    container_dir = Path(args.container_dir)
    log_dir = Path(args.log_dir)
    time_per_case = args.timeout   # seconds
    repeat_failed = args.repeat_failed
    use_cuda10 = False
    if args.container_cuda == 10:
        use_cuda10 = True

    logging.basicConfig(handlers=[logging.FileHandler(log_dir / "main.log"), logging.StreamHandler()],
                        level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("\n\n START EVALUATION RUN \n")

    # detect nvidia driver version
    try:
        gpu_info_csv = log_dir / 'gpu_info.csv'
        subprocess.run(
            shlex.split(f"nvidia-smi --query-gpu=name,driver_version --format=csv -f {gpu_info_csv}"),
        )
        with open(gpu_info_csv) as csv_file:
            csv_reader = csv.DictReader(csv_file, skipinitialspace=True)   # nvidia-smi puts a space after the comma...
            gpus = []
            for info_dict in csv_reader:
                gpus.append(info_dict)
        logging.info(f"Found {len(gpus)} GPUs with driver version(s) {[g['driver_version']for g in gpus]}.")
        # cotinuing with gpu 0 as this will be used per default
        driver_version = gpus[0]['driver_version'].split('.')
        major_version = driver_version[0]
        minor_version = driver_version[1]
        if args.container_cuda == 0:   # choose version automatically
            if int(major_version) < 450 or (int(major_version) == 450 and int(minor_version) < 51):
                use_cuda10 = True
                logging.info("Detected a driver that does not support CUDA 11 => Using containers based on CUDA 10.1 instead.")
    except:
        logging.warning(traceback.format_exc())
        logging.warning("Could not check gpu driver (see error above). Continuing without this info...")
    
    # curl config contains the url of the submission summary file to use
    if use_cuda10:
        curl_config = Path(__file__).parent / 'curlconfig_cuda10.txt'
    else:
        curl_config = Path(__file__).parent / 'curlconfig.txt'

    # download container summary
    submission_summary_path = log_dir / 'submission_summary.json'
    download_file(submission_summary_path, curl_config, raise_status=True)
    with open(submission_summary_path) as f:
        submission_list = json.load(f)
    order_of_evaluation = [x for x,y in sorted(enumerate([x['id'] for x in submission_list]), key = lambda x: x[1])]
    
    # I need to make another curl config file for the container downloads here
    curl_config_header = curl_config.parent / "curl_header"
    shutil.copy(curl_config, curl_config_header)
    with open(curl_config_header, 'r+') as f:
        text = f.read()
        text = re.sub(r'^url', '# url', text, flags=re.MULTILINE)
        f.seek(0)
        f.write(text)
        f.truncate()

    # Parse subject list from split file
    included_subjects = []
    with open(args.split_file, newline='') as csvfile:
        split_reader = csv.reader(csvfile)
        for row in split_reader:
            if str(row[0]) == 'data_uid':
                continue
            included_subjects.append(str(row[0]))
    logging.info(f"Read the following subjects from the split file: {', '.join(included_subjects)}")

    for subm_idx in order_of_evaluation:
        submission = submission_list[subm_idx]
        subm_id = submission["id"]
        url = submission["url"]

        curr_out_dir = output_dir / str(subm_id)
        curr_log_dir = log_dir / str(subm_id)
        curr_subm_summary_file = curr_log_dir / 'execution_summary.json'

        # reset logging config
        logging.info("================================")
        logging.info(f"Processing submission {subm_id}...")

        # maybe check if submission has already been run
        curr_out_dir.mkdir(exist_ok=True)
        if curr_subm_summary_file.exists():
            if repeat_failed:
                with open(curr_subm_summary_file) as f:
                    tmp_dict = json.load(f)
                    if tmp_dict['status'] == EXIT_STATUS['success']:
                        logging.info("Already successfully run. Skipping this submission!")
                        continue
                    # else repeat the evaluation
            else:
                logging.info("Already run (maybe with error). Skipping this submission!")
                continue

        if curr_log_dir.exists():
            # This indicates that a previous run exited with error (uncaught exception). Reset logs...
            shutil.rmtree(curr_log_dir)
        curr_log_dir.mkdir()

        # download container to container_dir (naming with submission id)
        sif_file = container_dir / f"{subm_id}.sif"
        n_download_attempts = 5
        sha256_sum = None
        for attempt in range(n_download_attempts):   # download attempts
            try:
                if not sif_file.exists() or \
                    (sif_file.exists() and sif_file.stat().st_size != submission['file_size']) or \
                    (sif_file.exists() and compute_sha256(sif_file) != submission['file_sha256']):
                    download_file(sif_file, curl_config_header, url=url, log_file=curr_log_dir / "download.log", raise_status=True)
                else:
                    logging.info("Found exisiting sif-file. Continuing without download...")

                # check container file
                check = True
                if sif_file.stat().st_size != submission['file_size']:
                    check = False
                else:
                    logging.info("Check SHA256 of container file...")
                    sha256_sum = compute_sha256(sif_file)
                    if sha256_sum != submission['file_sha256']:
                        check = False
                
                if not check:
                    logging.error("File size/checksum of the sif-file is not correct!")
                    if sif_file.stat().st_size < 1000:
                        shutil.copy(sif_file, curr_log_dir / "download_response.txt")   # educated guess that this is text file
                    raise RuntimeError("File size/checksum not correct; probably download problem.")
                else:
                    break   # check ok; don't attempt further downloads
            except:
                if attempt == n_download_attempts - 1:
                    raise
                else:
                    logging.info(f"Download failed; retrying (attempt {attempt + 2} of {n_download_attempts})...")

        # run container
        logging.info("Testing FeTS singularity image...")
        # This runs the container in the same way it is done in the testing phase
        status = EXIT_STATUS['success']
        try:
            chunk_size = 100
            runtime = 0
            for offset in range(len(included_subjects) // chunk_size + 1 * (len(included_subjects) % chunk_size > 0)):
                runtime += run_container(
                    sif_file,
                    in_dir=data_path,
                    out_dir=curr_out_dir,
                    subject_list=included_subjects[offset * chunk_size : min((offset + 1) * chunk_size, len(included_subjects))],
                    timeout_case=time_per_case,
                    log_file=curr_log_dir / "singularity.log"
                )
        except subprocess.TimeoutExpired as e:
            runtime = e.timeout
            logging.error(traceback.format_exc())
            status = EXIT_STATUS['timeout']
        except MissingData:
            raise
        except Exception:
            runtime = None
            logging.error(traceback.format_exc())
            status = EXIT_STATUS['error']
        logging.info(f"Runtime of the inference container: {runtime}")

        # clean-up output folder and sif file
        # delete excess files in output folder here (all but the segmentations)
        accepted_filenames = [f"{subj}_seg.nii.gz" for subj in included_subjects]
        logging.info("Cleaning up output directory")
        for out_path in curr_out_dir.iterdir():
            if out_path.is_dir():
                logging.warning(f"Deleting directory in output folder: {out_path.name}")
                shutil.rmtree(out_path)
            elif out_path.name not in accepted_filenames:
                logging.warning(f"Deleting file in output folder which does follow naming convention: {out_path.name}")
                out_path.unlink()
        
        if not args.keep_sif:
            # cleanup (delete container file)
            sif_file.unlink()

        # maybe save some file with exit status (in output dir?)
        summary_dict = {
            'status': status,
            'runtime': runtime,
            'predicted_cases': len(list(curr_out_dir.iterdir())),
            'total_cases': len(included_subjects)
        }
        with open(curr_subm_summary_file, 'w') as f:
            json.dump(summary_dict, f, indent=2)
        logging.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--container_dir", required=True, type=str,
        help="Path to the folder where .sif files will be saved. All containers will be run."
    )
    parser.add_argument(
        "-i", "--input_dir",required=True,type=str,
        help=("Input data lies here. Make sure it has the correct folder structure!"),
    )
    parser.add_argument(
        "-o", "--output_dir", required=True, type=str,
        help="Folder where the outputs/predictions will be written to"
    )
    parser.add_argument(
        "-l", "--log_dir", required=True, type=str,
        help="Folder where the logs will be written to"
    )
    parser.add_argument(
        "-s", "--split_file", required=True, type=str,
        help="CSV-file that contains the split that should be used for evaluation."
    )
    parser.add_argument(
        "-t", "--timeout", default=600, required=False, type=float,
        help="Time budget PER CASE in seconds. Evaluation will be stopped after the total timeout of timeout * n_cases."
    )
    parser.add_argument(
        "--keep_sif", action='store_true', required=False,
        help="Whether to keep the sif-file saved in the submission folder or delete it after the experiment."
    )
    parser.add_argument(
        "--repeat_failed", action='store_true', required=False,
        help="This forces a repetition of submissions that exited with errors."
    )
    parser.add_argument(
        "--container_cuda", default=0, required=False, type=int, choices=[0, 10, 11],
        help="Specify the cuda version the container should be based on. Possible values are 0 (= automatic), 10 and 11."
    )

    main(parser.parse_args())