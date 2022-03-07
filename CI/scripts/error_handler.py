import smtplib
import git
import os
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections.abc import Mapping


# kaapana_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
kaapana_dir = '/home/ubuntu/kaapana'
g = git.Git(kaapana_dir)


def send_email(mail_address, message, logs_dict={}):
    print("++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("SENDING EMAIL: {}".format(mail_address))
    print("MESSAGE: {}".format(message))
    print("++++++++++++++++++++++++++++++++++++++++++++++++++++")
    from_address = "CI@kaapana.dkfz"
    sending_ts = datetime.now()

    sub = 'Kaapana CI report'
    
    msgRoot = MIMEMultipart('related')
    msgRoot['From'] = from_address
    msgRoot['To'] = mail_address
    msgRoot['Subject'] = sub

    msgAlt = MIMEMultipart('alternative')
    msgRoot.attach(msgAlt)
    
    msgTxt = MIMEText(message, 'html')
    msgAlt.attach(msgTxt)
    
    if isinstance(logs_dict, Mapping):
        attachment = MIMEText(json.dumps(logs_dict, indent=4, sort_keys=True))
    else:
        attachment = MIMEText(logs_dict, 'plain')
    attachment.add_header('Content-Disposition', 'attachment', filename="logs.txt")
    msgRoot.attach(attachment)

    s = smtplib.SMTP(host='mailhost2.dkfz-heidelberg.de', port=25)
    s.sendmail(from_address, mail_address, msgRoot.as_string())
    s.quit()
    return 0


def notify_maintainers(logs_dict):
    print("notify_maintainers: ")    
    if "container" in logs_dict:
        del logs_dict["container"]
    maintainers = blame_last_edit(logs_dict)

    if maintainers is None:
        print("++++++++++++++++++++++ COULD NOT EXTRACT MAINTAINER!")
        return
    else:
        print("FILE MAINTAINERS: ")
        print(json.dumps(maintainers, indent=4, sort_keys=True))

    for maintainer in maintainers.keys():
        print("Maintainer: {} -> {}".format(maintainer, maintainers[maintainer]))
        maintainer_name = maintainer
        maintainer_email = maintainers[maintainer]

        error_filepath = os.path.dirname(logs_dict['rel_file']).replace("/home/ubuntu", "")

        message = """
            <html>
                <head></head>
                <body>
                    Hi <b>{}</b>,<br><br>

                    We found some issues within: <b> {} </b>.<br>
                    Since you are the last editor, please have a look at it.<br>
                    To view the CI launches, visit the following link:<br>
                    http://10.128.130.252/ui/#kaapana/launches/all<br>
                    and use the following credentials to login:<br>
                    user: read<br>
                    password: Read_1234<br>
                    Thanks!<br><br>
                    Yours sincerely,<br>
                    Kaapana-CI <br>
                </body>
            </html>
            """.format(maintainer_name, error_filepath)

        # send_email(mail_address=maintainer_email, message=message, logs_dict=logs_dict)
        send_email(mail_address="kaushal.parekh@dkfz-heidelberg.de", message=message, logs_dict=logs_dict)


def blame_last_edit(logs_dict):
    error_filepath = os.path.dirname(logs_dict['rel_file'])
    print("Git blame path: {}".format(error_filepath))
    
    if error_filepath == "" and error_filepath is None and not os.path.isfile(error_filepath) or not os.path.isdir(error_filepath):
        print("error_filepath is not a valid file or dir! -> return")
        return None
    ## Following condition only temporary until ci merged into develop
    if "kaapana_ci" in error_filepath:
        print("Error in file from CI folder on server: {}".format(error_filepath))
        return None

    git_log = g.log("-s", "-n1", "--pretty=format:%an %ae%n", "--", error_filepath)
    if len(git_log.split(" ")) != 3:
        print("############################################# Could not extract last editor: {}".format(git_log))
        return None

    firstname, lastname, email_address = git_log.split(" ")
    print("Git Last editor: {} {}".format(firstname, lastname))
    print("Git mail address: {}".format(email_address))

    return {"{} {}".format(firstname, lastname): email_address}
    # return {"{} {}".format(firstname, lastname): "kaushal.parekh@dkfz-heidelberg.de"}


def ci_failure_notification(message="", logs_dict={}):
    print("CI failure notification to Kaapana team members: ")
    # maintainer_email = "kaapana-team@dkfz-heidelberg.de"
    maintainer_email = "kaushal.parekh@dkfz-heidelberg.de"
    message = """
        <html>
            <head></head>
            <body>
                Hi,<br><br>

                This is to inform you that the Kaapana CI has failed. <b> {} </b>.<br>
                You are receiving this email since you are a part of the Kaapana team.<br>
                To view the CI launches, visit the following link:<br>
                http://10.128.130.252/ui/#kaapana/launches/all<br>
                and use the following credentials to login:<br>
                user: read<br>
                password: Read_1234<br>
                Thanks!<br><br>
                Yours sincerely,<br>
                Kaapana-CI <br>
            </body>
        </html>
        """.format(message)

    send_email(mail_address=maintainer_email, message=message, logs_dict=logs_dict)


def last_commit_author():
    git_log = g.log("-1", "--pretty=format:%an %ae%n")
    if len(git_log.split(" ")) != 3:
        print("############################################# Could not extract author details of last Git commit: {}".format(git_log))
        return None

    firstname, lastname, email_address = git_log.split(" ")
    print("Author of last Git commit: {} {}".format(firstname, lastname))
    print("Email of author of last Git commit: {}".format(email_address))

    return {"{} {}".format(firstname, lastname): email_address}


if __name__ == '__main__':
    # send_email(mail_address="jonas.scherer@dkfz-heidelberg.de", message="Here is a test message!")
    blame_last_edit("/home/jonas/projects/kaapana/workflows/docker-container/", logs_dict={"ERROR": "error."})
