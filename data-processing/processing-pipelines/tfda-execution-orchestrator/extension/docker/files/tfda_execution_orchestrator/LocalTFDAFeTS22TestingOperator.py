import json
import os
import synapseclient as sc
import smtplib
import logging
import subprocess
import yaml
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from synapseclient import Project, Folder, File, Link
from challengeutils import permissions, utils
from subprocess import PIPE
from airflow.exceptions import AirflowFailException
from airflow.models import DagRun
from airflow.api.common.experimental.get_dag_run_state import get_dag_run_state
from airflow.api.common.experimental.trigger_dag import trigger_dag as trigger
from airflow.api.common.experimental.get_dag_run_state import get_dag_run_state
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

class LocalTFDAFeTS22TestingOperator(KaapanaPythonBaseOperator):
    def extract_config(self, config_filepath):
        with open(config_filepath, "r") as stream:
            try:
                config_dict = yaml.safe_load(stream)
                return config_dict
            except yaml.YAMLError as exc:
                raise AirflowFailException(f"Could not extract configuration due to error: {exc}!!")

    def run_command(self, command):
        process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, encoding="Utf-8")
        while True:
            output = process.stdout.readline()
            if process.poll() is not None:
                break
            if output:
                print(output.strip())
        return_code = process.poll()
        return return_code


    def send_email(self, email_address, cc_address, message, filepath, subm_id):
        assert(email_address != "", "Please specify the recipient of the Email")
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("SENDING EMAIL: {}".format(email_address))
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++")
        from_address = ""
        # sending_ts = datetime.now()

        sub = f'FeTS 2022 Evaluation Result for Submission (ID: {subm_id})'
        
        msgRoot = MIMEMultipart('related')
        msgRoot['From'] = from_address
        msgRoot['To'] = email_address
        if cc_address is not None and cc_address != "":
            msgRoot['Cc'] = cc_address
        msgRoot['Subject'] = sub

        msgAlt = MIMEMultipart('alternative')
        msgRoot.attach(msgAlt)
        
        msgTxt = MIMEText(message, 'html')
        msgAlt.attach(msgTxt)
        
        # if filepath is not None and filepath != "":
        #     with open(filepath,'rb') as file:
        #         attachment = MIMEApplication(file.read())
        #     attachment.add_header('Content-Disposition', 'attachment', filename=f"results_{subm_id}_{sending_ts.strftime('%Y-%m-%d')}.zip")
        #     msgRoot.attach(attachment)

        s = smtplib.SMTP(host='mailhost2.dkfz-heidelberg.de', port=25)
        s.sendmail(from_address, msgRoot["To"].split(", ") + msgRoot["Cc"].split(", "), msgRoot.as_string())
        s.quit()
    
    def get_most_recent_dag_run(self, dag_id):
        dag_runs = DagRun.find(dag_id=dag_id)
        dag_runs.sort(key=lambda x: x.execution_date, reverse=True)
        return dag_runs[0] if dag_runs else None


    def start(self, ds, ti, **kwargs):
        synapse_user = ""
        API_KEY = ""
        synapse_pw = ""
        container_reg = "docker.synapse.org"
        operator_dir = os.path.dirname(os.path.abspath(__file__))
        subm_logs_path = os.path.join(operator_dir, "data", "subm_logs")
        tarball_path = os.path.join(operator_dir, "algorithm_files")
        subm_results_path = os.path.join(operator_dir, "results")
        singularity_images_path = os.path.join(operator_dir, "singularity_images")
        platform_config_path = os.path.join(operator_dir, "platform_specific_configs", "platform_config.yaml")
        request_config_path = os.path.join(operator_dir, "request_specific_configs", "request_config.yaml")
        tasks = [("fets_2022_test_queue", 9615030)]
        # tasks = [("FeTS 2022 Task 2 Docker Submissions Queue", 9615036)]

        logging.info("Loading platform and request specific configurations...")
        platform_config = self.extract_config(platform_config_path)
        request_config = self.extract_config(request_config_path)

        subm_dict = {}
        subm_dict_path = os.path.join(subm_logs_path, "subm_dict.json")

        if os.path.exists(subm_dict_path):
            with open(subm_dict_path, "r") as fp_:
                subm_dict = json.load(fp_)
        
        logging.info("Logging into Synapse...")
        syn = sc.login(email=synapse_user, apiKey=API_KEY)

        logging.info("Logging into container registry!!!") 
        command = ["skopeo", "login", "--username", f"{synapse_user}", "--password", f"{synapse_pw}", f"{container_reg}"]
        return_code = self.run_command(command=command)
        if return_code == 0:
            logging.info(f"Login to the registry successful!!")
        else:
            raise AirflowFailException("Login to the registry FAILED! Cannot proceed further...")
        
        logging.info("Checking for new submissions...")
        for task_name, task_id in tasks:
            print(f"Checking {task_name}...")
            for subm in syn.getSubmissions(task_id, status="RECEIVED"):      
                subm_id = subm["id"]
                if subm_id not in subm_dict or subm_dict.get(subm_id) != "success":
                    print(f"Pulling container with submission ID: {subm_id}...")
                    tarball_file = os.path.join(tarball_path, f"{subm_id}.tar")
                    if os.path.exists(tarball_file):
                        print(f"Submission tarball already exists locally... deleting it now to pull latest!!")
                        os.remove(tarball_file)
                    command2 = ["skopeo", "copy", f"docker://{subm['dockerRepositoryName']}@{subm['dockerDigest']}", f"docker-archive:{tarball_file}", "--additional-tag", f"{subm_id}:latest"]
                    return_code2 = self.run_command(command=command2)
                    if return_code2 != 0:
                        logging.error(f"Error while trying to download container! Skipping...")
                        subm_dict[subm_id] = "skipped"
                        continue
                    
                    self.trigger_dag_id = "dag-tfda-execution-orchestrator"
                    # self.dag_run_id = kwargs['dag_run'].run_id
                    self.conf = kwargs['dag_run'].conf
                    self.conf["platform_config"] = platform_config
                    self.conf["request_config"] = request_config
                    dag_run_id = generate_run_id(self.trigger_dag_id)
                    logging.info("Triggering isolated execution orchestrator...")
                    try:
                        trigger(dag_id=self.trigger_dag_id, run_id=dag_run_id, conf=self.conf,
                                        replace_microseconds=False)
                    except Exception as e:
                        logging.error(f"Error while triggering isolated workflow for submission with ID: {subm_id}...")
                        logging.error(e)
                        subm_dict[subm_id] = "exception"

                    dag_run = self.get_most_recent_dag_run(self.trigger_dag_id)
                    if dag_run:
                        print(f"The latest isolated workflow has been triggered at: {dag_run.execution_date}!!!")

                    dag_state = get_dag_run_state(dag_id="tfda-execution-orchestrator", execution_date=dag_run.execution_date)

                    while dag_state["state"] != "failed" and dag_state['state'] != "success":
                        dag_run = self.get_most_recent_dag_run(self.trigger_dag_id)
                        dag_state = get_dag_run_state(dag_id="tfda-execution-orchestrator", execution_date=dag_run.execution_date)                        
                    
                    sending_ts = datetime.now()
                    subm_results_file = f"{subm_results_path}/results_{subm_id}_{sending_ts.strftime('%Y-%m-%d')}.zip"

                    if os.path.exists(subm_results_file):
                        subm_results = subm_results_file
                        try:
                            print("Uploading results to Synpase...")
                            syn_usr_folder = Folder(f"{subm['userId']}", parent="syn32177645")
                            syn_usr_folder = syn.store(syn_usr_folder)
                            
                            ## Update permissions for folders containing submissions
                            permissions.set_entity_permissions(syn, entity=syn_usr_folder, principalid=subm['userId'], permission_level="download")

                            syn_subm_folder = Folder(f"{subm_id}", parent=syn_usr_folder)
                            syn_subm_folder = syn.store(syn_subm_folder)                            

                            push_results = File(subm_results_file, description=f"Results/logs for submission: {subm_id}", parent=syn_subm_folder)
                            push_results = syn.store(push_results)
                            
                            syn_subm_res_link = f"https://www.synapse.org/#!Synapse:{syn_subm_folder['id']}"
                        except:
                            print("Could not upload results files to Synapse, no link will be provided to the users...")
                            syn_subm_res_link = "Sorry! Unfortunately, result files couldn't be uploaded for your submission. Please respond to all from this Email to clarify why this happened."
                    else:
                        subm_results = None
                        syn_subm_res_link = "Sorry! Unfortunately, result files were not generated for your submission. Please respond to all from this Email to clarify why this happened."
                    
                    # Get Synapse user ID
                    try:
                        synapse_id = syn.getTeam(subm["userId"]).get('name')
                    except sc.core.exceptions.SynapseHTTPError:
                        synapse_id = syn.getUserProfile(subm["userId"]).get('userName')
                    cc_address = ""
                    synapse_email_id = f"{synapse_id}@synapse.org"

                    if dag_state["state"] == "failed":
                        print(f"**************** The evaluation of submission with ID {subm_id} has FAILED ****************")
                        subm_dict[subm_id] = "failed"
                        ## Email report
                        message = """
                        <html>
                            <head></head>
                            <body>
                                Dear {},<br><br>
                                Thank you for your submission (ID: {}) to the FeTS challenge 2022 task 2! We tested your container on the toy dataset and you can download the results from:<br>
                                {}<br>
                                Unfortunately, the evaluation of your container was not successful; please check the logs (medperf.log), which contain some debugging information. If you have problems identifying the issue, just respond to all from this email and we will do our best to get your submission running.<br>
                                <br><br>
                                Yours sincerely,<br>
                                The FeTS challenge organizers <br>
                            </body>
                        </html>
                        """.format(synapse_id, subm_id, syn_subm_res_link)
                        utils.change_submission_status(syn, subm_id, status="INVALID")
                        self.send_email(email_address=synapse_email_id, cc_address=cc_address, message=message, filepath=subm_results, subm_id=subm_id)
                    if dag_state["state"] == "success":
                        print(f"**************** The evaluation of submission with ID {subm_id} was SUCCESSFUL ****************")
                        subm_dict[subm_id] = "success"
                        ## Email report
                        message = """
                        <html>
                            <head></head>
                            <body>
                                Dear {},<br><br>
                                Thank you for your submission (ID: {}) to the FeTS challenge 2022 task 2! We tested your container on the toy dataset and you can download the results from:<br>
                                {}<br>
                                Looks like there were no fatal errors during the evaluation of your container, great! However, to make sure everything ran correctly, please check the results.yaml file and compare it with your local results. Watch out for discrepancies, as they may indicate reproducibility issues. If you have any questions, feel free to post them in the <a href="https://www.synapse.org/#!Synapse:syn28546456/discussion/default">discussion forum</a> or respond to all from this email directly.<br>
                                <br><br>
                                Cheers!<br>
                                The FeTS challenge organizers <br>
                            </body>
                        </html>
                        """.format(synapse_id, subm_id, syn_subm_res_link)
                        utils.change_submission_status(syn, subm_id, status="ACCEPTED")
                        self.send_email(email_address=synapse_email_id, cc_address=cc_address, message=message, filepath=subm_results, subm_id=subm_id)

                        # Rename singularity file that was copied from isolated instance
                        singularity_file = os.path.join(singularity_images_path, "dockersynapseorgsyn31437293fets22modellatest.sif")
                        singularity_file_rename = os.path.join(singularity_images_path, f"{subm_id}.sif")
                        os.rename(singularity_file, singularity_file_rename)
                else:
                    print("Submission already SUCCESSFULLY evaluated!!!!")

                print(f"Saving submission dict...")
                with open(subm_dict_path, "w") as fp_:
                    json.dump(subm_dict, fp_)

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="fets22-evaluate-submissions",
            python_callable=self.start,
            **kwargs
        )