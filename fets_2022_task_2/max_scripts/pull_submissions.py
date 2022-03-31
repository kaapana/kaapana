"""
What to do here (pipelines correpond to submissions):

For each project in fets group:
1. list pipelines and filter for successful ones on the "submission" branch
2. Check if there are new pipelines
3. For the new pipelines, download the submission.json files and add them to the submission dataframe (with status 'open')

Pull submissions:
For each submission in dataframe with status open, pull the container file to a hardcoded path
"""

from argparse import ArgumentParser
from datetime import datetime
import json
from json.decoder import JSONDecodeError
import logging
from logging.handlers import SMTPHandler
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import traceback
import sys
from time import localtime, strftime
import time
import smtplib
import ssl
from email.message import EmailMessage

from dateutil.parser import isoparse
from dateutil import tz
import pandas as pd
import requests


# For resolving import issues 
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))


# Each submission has its own directory, including a metrics.json and an failed/end.txt indicating its status
def sync_from_cluster(cluster_path: Path, local_path: Path, exclude_files=[], include_files=[]):
    try:
        exclude_str = ""
        for f in exclude_files:
            exclude_str += f" --exclude='{f}'"
        include_str = ""
        for f in include_files:
            include_str += f" --include='{f}'"
        copy_str = (
            f"rsync -rav "
            f"{exclude_str} {include_str} --include='*/' --include='/*/*.json'  --include='/*/*.txt' --include='/*/*.log' --exclude='*' "
            f"cluster-node:{cluster_path}/ {local_path}"
        )
        logging.info(copy_str)
        subprocess.run(
            shlex.split(copy_str),
            check=True,
        )
    except Exception as e:
        logging.error("Syncing files failed...")
        raise e


def json_to_cluster(json_path: Path, cluster_dir: Path):
    try:
        copy_str = (
            f"rsync -av {json_path.absolute()} cluster-node:{cluster_dir}"
        )
        subprocess.run(
            shlex.split(copy_str),
            check=True,
        )
    except Exception as e:
        logging.error("Syncing files failed...")
        raise e


def run_on_cluster(submission_id, cluster_script: Path, **kwargs):
    gpu_model = "GeForceRTX2080Ti"   # can be found in lsload -gpuload -w
    kwargs_str = ""
    for k, v in kwargs.items():
        if v is None:
            # case for option without value
            kwargs_str += f" --{k}"
        else:
            kwargs_str += f" --{k} {v}"
    sq = '\\ESC'   # annoying bash escaping
    cluster_cmd = (
        f"bsub -R 'select[hname!={sq}hdf18-gpu16{sq}]' -R 'rusage[mem=40G]' -gpu num=1:j_exclusive=yes:mode=exclusive_process:gmodel={gpu_model} -L /bin/bash -q gpu "
        f"'source ~/.bashrc_fets && python {cluster_script} {submission_id} {kwargs_str}'"
    )

    # This will be passed to bash with "cluster_cmd" and hence escaped double-quotes should be used
    cluster_cmd = cluster_cmd.replace("'", '\\"')
    cluster_cmd = cluster_cmd.replace(sq, "\'\"\'\"\'")
    shell_cmd = (
        f"ssh cluster-lsf 'bash -lc \"{cluster_cmd}\"'"
    )
    logging.info("Starting job on the cluster with the following command:\n" + shell_cmd)
    subprocess.run(shlex.split(shell_cmd), check=True)


def is_submission_ok(submission_dict, project_id, t_submitted):
    # checks for late submissions and package issues
    # Is submission time within deadline?
    delta_t = isoparse(t_submitted) - SUBM_DEADLINE
    if delta_t.total_seconds() / 60 > 0:
        logging.error("ERROR: late submission detected."
                        " This should not happen unless the participants retry the save-submission job at a later time."
                        " Contact the submitting team for clarification!")
        return False

    # Checks of package:
    pkg_id = submission_dict['package_id']

    # Does package_name and version match the package_id? (not sure if necessary)
    url = f"{BASE_URL}/projects/{project_id}/packages/{pkg_id}"
    logging.debug(f"GET {url}")
    r = requests.get(url, headers=TOKEN_HEADER)
    if r.status_code == 200:
        pkg_dict = r.json()
        if pkg_dict["name"] != submission_dict["package_name"] or \
                pkg_dict["version"] != submission_dict["package_version"] or \
                pkg_dict["package_type"] != "generic":
            logging.error(f"Something is wrong with the package (either name/version do not match submitted information or not generic package).")
            return False
    else:
        logging.error(f"API call returned with status {r.status_code}.")
        logging.error(r.text)
        return False
    
    # Check that there is only one file in package
    url = f"{BASE_URL}/projects/{project_id}/packages/{pkg_id}/package_files"
    logging.debug(f"GET {url}")
    r = requests.get(url, headers=TOKEN_HEADER)
    if r.status_code == 200:
        file_list = r.json()
        if len(file_list) != 1:
            logging.error(f"There should be exactly one file in the packge (sif-file), but found {len(file_list)}.")
            return False
        if not file_list[0]['file_name'].endswith(".sif"):
            logging.error(f"It seems like the file in the package is not a .sif file: {file_list[0]['file_name']}.")
            return False
    else:
        logging.error(f"API call returned with status {r.status_code}.")
        logging.error(r.text)
        return False
    
    pkg_file = file_list[0]
    # Was package file created before submission deadline?
    delta_t = isoparse(pkg_file["created_at"]) - SUBM_DEADLINE
    if delta_t.total_seconds() / 60 > 0:
        logging.error("ERROR: late submission detected."
                        " This should not happen unless the participants touched the pipeline."
                        " Contact the submitting team for clarification!")
        return False

    # Is file sha identical to the one saved in submission dict?
    if pkg_file['file_sha256'] != submission_dict['file_sha256']:
        logging.error("ERROR: sha256 of submitted file does not match checksum of current package file. "
                        "This indicates that the file changed for some reason (e.g. deleted file and re-uploaded). "
                        "Contact the submitting team!")
        return False
    return True


def collect_new_submissions(project_id, old_submissions=None):
    if old_submissions is None:
        old_submissions = []
    new_submissions = []
    # get pipelines in project's submission_branch (equivalent to submissions)
    url = BASE_URL + f"/projects/{project_id}/pipelines"
    logging.debug(f"GET {url}")
    r = requests.get(
        url,
        headers=TOKEN_HEADER,
        params={'status': 'success', 'ref': SUBM_BRANCH, 'per_page': 100}
    )
    if r.status_code != 200:
        logging.error(f"API call returned with status {r.status_code}.")
        logging.error(r.text)
        return new_submissions
    if int(r.headers['x-total-pages']) > 1:
        raise NotImplementedError("There were too many pages in the API response. This should only happen if a team has A LOT of submissions.")
    
    for pipeline in r.json():
        assert pipeline["status"] == "success"
        if pipeline["id"] in old_submissions:
            # already registered submission
            continue
        # get submission dict from job artifact
        url = BASE_URL + f"/projects/{project_id}/pipelines/{pipeline['id']}/jobs"
        logging.debug(f"GET {url}")
        r = requests.get(url, headers=TOKEN_HEADER)
        # This will not return jobs that were retried unless specified in params => only latest jobs in list
        for job in r.json():
            if job["name"] == "save-submission":
                url = BASE_URL + f"/projects/{project_id}/jobs/{job['id']}/artifacts/submission.json"
                logging.debug(f"GET {url}")
                try:
                    submission_dict = requests.get(url, headers=TOKEN_HEADER).json()
                except JSONDecodeError:
                    logging.error(f"Could not decode json response from {url}\n")
                    continue
                
                t_submitted = job["started_at"]
                if not is_submission_ok(submission_dict, project_id, t_submitted):
                    logging.error("Some checks for this submission failed. Investigate!")
                    continue

                url =  (
                    f"{BASE_URL}/projects/{project_id}/packages/generic/"
                    f"{submission_dict['package_name']}/{submission_dict['package_version']}/{submission_dict['file_name']}"
                )
                # TODO the consistent definition of keys is not solved well here (need to have matching keys in other project)
                new_submissions.append({
                    'id': pipeline["id"],
                    'status': STATUS['open'],
                    'submission_time': t_submitted,
                    'user_name': submission_dict['user_name'],
                    'user_email': submission_dict['user_email'],
                    'project_id': project_id,
                    'package_id': submission_dict['package_id'],
                    'package_name': submission_dict['package_name'],
                    'package_version':  submission_dict['package_version'],
                    'file_id': submission_dict['file_id'],
                    'file_created_at': submission_dict['file_created_at'],
                    'file_name': submission_dict['file_name'],
                    'file_size': submission_dict['file_size'],
                    'file_sha256': submission_dict['file_sha256'],
                    'url': url,
                })
    return new_submissions


def update_submission_status(row):
    id = row['id']
    result_dir = local_base_path / f"{id}"
    status = row['status']
    if status == STATUS['open'] or status == STATUS['running']:
        if result_dir.exists():
            status = STATUS['running']
        if (result_dir / "success.txt").exists():
            status = STATUS['done']
        elif (result_dir / "fail.txt").exists():
            status = STATUS['failed']
            logging.error(f"Submission {id} failed on cluster. Need to check...")
    row['status'] = status
    return row


def main():
    json_kwargs = {
        'orient': 'index',
    }

    with open(project_list_path) as f:
        project_whitelist = json.load(f)
        r = requests.get(BASE_URL + f"/groups/{FETS_GROUP}/projects", headers=TOKEN_HEADER)
        r.raise_for_status()
        all_fets_projects = r.json()
        all_fets_projects = [p["id"] for p in all_fets_projects]
        for proj in project_whitelist:
            if proj not in all_fets_projects:
                logging.error(f"Seems like project {proj} is not part of FeTS. Check whitelist!")
    # project_whitelist = requests.get(base_url + f"/groups/{fets_group}/projects", headers=headers).json()   # for testing

    if not submission_file_path.exists() or os.stat(submission_file_path).st_size == 0:
        submission_df = pd.DataFrame()
        logging.warning("json file with table of submissions not found. Creating new one.")
    else:
        submission_df = pd.read_json(submission_file_path, **json_kwargs)
    
    logging.info("Check for new submissions...")
    new_submissions = []
    old_submissions = []
    if len(submission_df) > 0:
        old_submissions = submission_df["id"].tolist()
    for project_id in project_whitelist:
        logging.info(f"Checking project {project_id}...")
        new_submissions.extend(
            collect_new_submissions(project_id, old_submissions=old_submissions)
        )

    if len(new_submissions) > 0:
        if len(submission_df) > 0:
            submission_df = submission_df.append(new_submissions, ignore_index=True)
        else:
            submission_df = pd.DataFrame(new_submissions)
    elif len(submission_df) == 0:
        logging.warning("There are no existing or new submissions. Nothing to do here... Exiting...")
        return

    if len(new_submissions) > 0:
        logging.info(f"Found {len(new_submissions)} new submissions!")
        # backup old file and save new one
        if submission_file_path.exists():
            backup_path = local_base_path / 'backup'
            backup_path.mkdir(exist_ok=True)
            backup_name = submission_file_path.stem + strftime("%Y-%m-%d-%H-%M-%S", localtime()) + '.json'
            shutil.copy(submission_file_path, backup_path / backup_name)
    else:
        logging.info("No new submissions!")

    logging.info("Getting results from cluster...")
    sync_from_cluster(cluster_base_path, local_base_path, exclude_files=[submission_file_name])
    # update submission status based on cluster files
    if reset_id is not None and reset_id in submission_df.id.to_list():
        # reset in table and submission directory
        logging.info(f"Resetting submission {reset_id} to OPEN...")
        submission_df.loc[submission_df['id'] == reset_id, 'status'] = STATUS['open']
        subm_dir = local_base_path / str(reset_id)
        if subm_dir.exists():
            shutil.rmtree(subm_dir)
    submission_df = submission_df.apply(update_submission_status, axis=1, result_type='broadcast')
    
    # build list of submissions to test on cluster
    ids_going_to_cluster = []
    open_submissions = submission_df[submission_df["status"] == STATUS['open']]
    num_subm_per_team = submission_df[
        submission_df["status"].isin([STATUS['done'], STATUS['running'], STATUS['failed']])
        ].groupby('project_id').size()
    for proj_id in submission_df.project_id.unique():
        if proj_id not in num_subm_per_team.index:
            num_subm_per_team = num_subm_per_team.append(pd.Series({proj_id: 0}))
    for row in open_submissions.itertuples():
        if num_subm_per_team[row.project_id] < MAX_SUBMISSION_COUNT:
            num_subm_per_team.at[row.project_id] += 1
            ids_going_to_cluster.append(row.id)
        else:
            submission_df.loc[submission_df.id == row.id, "status"] = STATUS["exceeded"]
            logging.warning(f"The following submission exceeds its team's budget of test submissions: {row.id} (team {row.project_id})")
            send_mail_exceeded(row._asdict())

    # Submission file is saved even if no new submissions have arrived to update statuses
    with open(submission_file_path, 'w') as f:
            submission_df.to_json(f, indent=2, date_format='iso', **json_kwargs)

    logging.info("Sending submission table to cluster...")
    json_to_cluster(submission_file_path, cluster_base_path)

    if to_cluster:
        for subm_id in ids_going_to_cluster:
            logging.info("===========================================")
            logging.info(f"Processing submission {subm_id}...")

            if (local_base_path / str(subm_id)).exists():
                logging.info(f"A results directory for this submission exists."

    # TODO alternative to having so many global variables?
    to_cluster = not args.no_cluster
    reset_id = args.set_open
    TOKEN_HEADER = {"PRIVATE-TOKEN": args.token}
    BASE_URL = "https://gitlab.hzdr.de/api/v4"
    FETS_GROUP = 3771
    SUBM_BRANCH = 'submission'
    SUBM_DEADLINE = datetime(2022, 7, 26, 23, 59, 59, tzinfo=tz.gettz('US/Eastern'))
    MAX_SUBMISSION_COUNT = 10
    TIME_PER_CASE = 180   # seconds
    STATUS = {
        'open': 'OPEN',
        'running': 'RUNNING',
        'done': 'DONE',
        'failed': 'FAILED',
        'exceeded': 'EXCEEDED'
    }

    # Paths
    local_base_path = Path('/mnt/datasets/fets_challenge/submissions')
    submission_file_name = 'all_submissions.json'
    submission_file_path = local_base_path / submission_file_name
    project_list_path = local_base_path / 'project_whitelist.json'
    cluster_base_path = Path('/home/m167k/my_checkpoint_dir/fets_challenge/submissions')
    cluster_script_path = Path('/home/m167k/git_repos/fets-challenge/Task_2/internal/test_submission_cluster.py')
    log_path = local_base_path / 'puller.log'

    # for error notifications:
    mail_handler = SMTPHandler(
        "mailhost2.dkfz-heidelberg.de",
        fromaddr="m.zenk@dkfz-heidelberg.de",
        toaddrs="m.zenk@dkfz-heidelberg.de",
        subject="[LOG] Error in submission puller.",
        secure=ssl._create_unverified_context())
    mail_handler.setLevel(logging.ERROR)
    logging.basicConfig(
        handlers=[logging.FileHandler(log_path),
                  logging.StreamHandler(),
                  mail_handler],
                  level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        while(True):
            logging.info("\n\n NEW RUN \n")
            main()
            if args.repeat_after < 0:
                break
            time.sleep(60 * args.repeat_after)
    except:
        smtp_server = "mailhost2.dkfz-heidelberg.de"
        port = 25
        context = ssl._create_unverified_context()

        sender = "m.zenk@dkfz-heidelberg.de"
        recipient = "m.zenk@dkfz-heidelberg.de"

        msg_content = f"The submission collection script crashed. Check the logs at {log_path}. " \
                      f"Traceback:\n{traceback.format_exc()}"

        with smtplib.SMTP(smtp_server, port) as server:

            server.ehlo()  # Can be omitted
            server.starttls(context=context)  # Secure the connection
            server.ehlo()

            # Open the plain text file whose name is in textfile for reading.
            # Create a text/plain message
            msg = EmailMessage()
            msg.set_content(msg_content)

            msg["Subject"] = f"[FeTS] Error in submission puller"
            msg["From"] = sender
            msg["To"] = recipient

            server.sendmail(sender, recipient, msg.as_string())