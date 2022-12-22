import json
import os
import getpass
import requests
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from minio import Minio

from subprocess import PIPE, run
from airflow.exceptions import AirflowFailException
from airflow.models import DagRun
from airflow.api.common.experimental.get_dag_run_state import get_dag_run_state
from airflow.api.common.trigger_dag import trigger_dag as trigger
from airflow.api.common.experimental.get_dag_run_state import get_dag_run_state
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

class LocalTFDAVettingBraTSOperator(KaapanaPythonBaseOperator):
    def send_email(self, email_address, cc_address, subject, message, filepath, container_name):
        assert(email_address != "", "Please specify the recipient of the Email")
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("SENDING EMAIL: {}".format(email_address))
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++")
        from_address = ""
        sending_ts = datetime.now()
        
        msgRoot = MIMEMultipart('related')
        msgRoot['From'] = from_address
        msgRoot['To'] = email_address
        if cc_address is not None and cc_address != "":
            msgRoot['Cc'] = cc_address
        msgRoot['Subject'] = subject

        msgAlt = MIMEMultipart('alternative')
        msgRoot.attach(msgAlt)
        
        msgTxt = MIMEText(message, 'html')
        msgAlt.attach(msgTxt)
        
        if filepath is not None and filepath != "":
            with open(filepath,'rb') as file:
                attachment = MIMEApplication(file.read())
            attachment.add_header('Content-Disposition', 'attachment', filename=f"results_{container_name}_{sending_ts.strftime('%Y-%m-%d')}.zip")
            msgRoot.attach(attachment)

        s = smtplib.SMTP(host='mailhost2.dkfz-heidelberg.de', port=25)
        s.sendmail(from_address, msgRoot["To"].split(", ") + msgRoot["Cc"].split(", "), msgRoot.as_string())
        s.quit()
    
    def extract_config(self, config_filepath):
        with open(config_filepath, "r") as stream:
            try:
                config_dict = json.load(stream)
                return config_dict
            except Exception as exc:
                raise AirflowFailException(f"Could not extract configuration due to error: {exc}!!")
    
    def get_most_recent_dag_run(self, dag_id):
        dag_runs = DagRun.find(dag_id=dag_id)
        dag_runs.sort(key=lambda x: x.execution_date, reverse=True)
        return dag_runs[0] if dag_runs else None

    def start(self, ds, ti, **kwargs):
        # Create client object with access and secret key.
        user = ""
        password = ""
        client = Minio("", user, password)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        subm_logs_path = os.path.join(base_dir, "data", "subm_logs")
        subm_results_path = os.path.join(base_dir, "results")
        images_path = os.path.join(base_dir, "brats_containers")
        platform_config_path = os.path.join(base_dir, "platform_specific_configs", "platform_config.json")
        request_config_path = os.path.join(base_dir, "request_specific_configs", "request_config.json")

        logging.info("Loading platform and request specific configurations...")
        platform_config = self.extract_config(platform_config_path)
        request_config = self.extract_config(request_config_path)

        subm_dict = {}
        subm_dict_path = os.path.join(subm_logs_path, "subm_dict.json")

        if os.path.exists(subm_dict_path):
            with open(subm_dict_path, "r") as fp_:
                subm_dict = json.load(fp_)

        print("Get BraTS containers list from DKFZ S3...")       
        objects = client.list_objects("e230-fets", prefix="extra_submissions/")
        for obj in objects:
            print("*********************************************")
            print(f"S3 Bucket name: {obj.bucket_name}")
            print(f"Container filename: {obj.object_name}")
            container_file = obj.object_name.split('/')[-1]
            container_name = container_file.split(".sif")[0]
            container_filepath = os.path.join(images_path, container_file)
            if os.path.exists(container_filepath):
                print(f"Container file already exists locally! Skipping download...")
            else:
                print(f"Downloading container: {container_name}...")
                try:
                    client.fget_object(obj.bucket_name, obj.object_name, file_path=container_filepath)
                except Exception as e:
                    print(f"Error while trying to download container: {e}!! Skipping...")
                    subm_dict[container_name] = "skipped"
                    continue

            if container_name not in subm_dict or subm_dict.get(container_name) != "success":                
                print("Triggering isolated execution orchestrator...")
                self.trigger_dag_id = "tfda-execution-orchestrator"
                self.conf = kwargs['dag_run'].conf
                self.conf["container_name"] = container_name
                self.conf["platform_config"] = platform_config
                self.conf["request_config"] = request_config
                dag_run_id = generate_run_id(self.trigger_dag_id)
                try:
                    trigger(dag_id=self.trigger_dag_id, run_id=dag_run_id, conf=self.conf,
                                    replace_microseconds=False)
                except Exception as e:
                    logging.error(f"Error while triggering isolated workflow for submission: {container_name}...")
                    logging.error(e)
                    subm_dict[container_name] = "exception"

                dag_run = self.get_most_recent_dag_run(self.trigger_dag_id)
                if dag_run:
                    logging.debug(f"The latest isolated workflow has been triggered at: {dag_run.execution_date}!!!")

                dag_state = get_dag_run_state(dag_id="tfda-execution-orchestrator", execution_date=dag_run.execution_date)

                while dag_state["state"] != "failed" and dag_state['state'] != "success":
                    dag_run = self.get_most_recent_dag_run(self.trigger_dag_id)
                    dag_state = get_dag_run_state(dag_id="tfda-execution-orchestrator", execution_date=dag_run.execution_date)                        
                
                sending_ts = datetime.now()
                subm_results_file = f"{subm_results_path}/results_{container_name}_{sending_ts.strftime('%Y-%m-%d')}.zip"

                if os.path.exists(subm_results_file):
                    subm_results = subm_results_file
                else:
                    subm_results = None

                if dag_state["state"] == "failed":
                    print(f"**************** The evaluation of submission {container_name} has FAILED ****************")
                    subm_dict[container_name] = "failed"
                if dag_state["state"] == "success":
                    print(f"**************** The evaluation of submission {container_name} was SUCCESSFUL ****************")
                    subm_dict[container_name] = "success"
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
            name="container-images-vetting",
            python_callable=self.start,
            **kwargs
        )