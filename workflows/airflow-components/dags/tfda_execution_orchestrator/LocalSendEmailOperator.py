import os
import glob
import zipfile
from subprocess import PIPE, run
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

operator_dir = os.path.dirname(os.path.abspath(__file__))
subm_results_path = os.path.join(operator_dir, "subm_results")

class LocalSendEmailOperator(KaapanaPythonBaseOperator):
    def send_email(self, email_address, message, filepath, subm_id):
        assert(email_address != "", "Please specify the recipient of the Email")
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("SENDING EMAIL: {}".format(email_address))
        print("MESSAGE: {}".format(message))
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++")
        from_address = "CI@kaapana.dkfz"
        sending_ts = datetime.now()

        sub = f'Evaluation Results for submission (ID:{subm_id}) FeTS 2022'
        
        msgRoot = MIMEMultipart('related')
        msgRoot['From'] = from_address
        msgRoot['To'] = email_address
        msgRoot['Subject'] = sub

        msgAlt = MIMEMultipart('alternative')
        msgRoot.attach(msgAlt)
        
        msgTxt = MIMEText(message, 'html')
        msgAlt.attach(msgTxt)

        with open(filepath,'rb') as file:
            attachment = MIMEApplication(file.read())
        attachment.add_header('Content-Disposition', 'attachment', filename=f"result_{sending_ts.strftime('%Y_%m_%d')}.zip")
        msgRoot.attach(attachment)

        s = smtplib.SMTP(host='mailhost2.dkfz-heidelberg.de', port=25)
        s.sendmail(from_address, email_address, msgRoot.as_string())
        s.quit()

    def start(self, ds, ti, **kwargs):
        subm_id = kwargs["dag_run"].conf["subm_id"]
        message = """
        <html>
            <head></head>
            <body>
                Hi,<br><br>
                The result from the evaluation of the submission (ID: {}) is attached to the email.<br>
                Thanks!<br><br>
                Yours sincerely,<br>
                The TFDA Team <br>
            </body>
        </html>
        """.format(subm_id)
        self.send_email(email_address="", message=message, filepath=f"{subm_results_path}/{subm_id}_results.zip", subm_id=subm_id)


    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="send-results-email",
            python_callable=self.start,
            **kwargs
        )