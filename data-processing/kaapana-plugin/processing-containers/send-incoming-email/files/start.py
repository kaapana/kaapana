    

from datetime import timedelta
import os
from pathlib import Path
import glob
import pydicom

from kaapanapy.logger import get_logger
from email.message import EmailMessage
import smtplib
from kaapanapy.helper import load_workflow_config
EMAIL = ""


WORKFLOW_CONFIG = load_workflow_config()
USERNAME = WORKFLOW_CONFIG.get("workflow_form").get("username")
logger = get_logger(__name__)

def dicom_value(ds, keyword, default=""):
    elem = ds.get(keyword, None)
    
    if elem is None:
        return default
    
    if hasattr(elem, 'value'):
        val = elem.value
    else:
        val = elem

    return str(val) if val is not None else default


def format_tags_as_html(tags: dict) -> str:
    rows = []
    for key, value in tags.items():
        display_value = value if value else "—"
        rows.append(
            f"""
            <tr>
                <td style="padding:6px 10px; font-weight:600; background:#f5f5f5;">{key}</td>
                <td style="padding:6px 10px;">{display_value}</td>
            </tr>
            """
        )

    return f"""
    <table border="1" cellspacing="0" cellpadding="0"
           style="border-collapse:collapse; font-family:Arial, sans-serif; font-size:13px;">
        {''.join(rows)}
    </table>
    """

def start():

    send_dir = os.path.join(
        "/", os.environ["WORKFLOW_DIR"], os.environ["OPERATOR_IN_DIR"]
    )
    logger.info(send_dir)
    for dicom_dir, _, _ in os.walk(send_dir):
        dicom_list = [
            f
            for f in Path(dicom_dir).glob("*")
            if f.is_file() and pydicom.misc.is_dicom(f)
        ]

        if len(dicom_list) == 0:
            continue

        try:
            ds = pydicom.dcmread(dicom_list[0])

            tags = {
                "PatientID": dicom_value(ds, "PatientID"),
                "PatientName": dicom_value(ds, "PatientName"),
                "AccessionNumber": dicom_value(ds, "AccessionNumber"),
                "StudyDescription": dicom_value(ds, "StudyDescription"),
                "StudyDate": dicom_value(ds, "StudyDate"),
                "InstitutionName": dicom_value(ds, "InstitutionName"),
            }

        except Exception as e:
            logger.error(f"Error reading DICOM file {dicom_list[0]}: {e}")
            continue

        send_email_notification(tags, )
        # upload_dcm_files does a walk through the directory and uploads all the dcm files

def send_email_notification(tags: dict):
    """
    Sends an email notification with dicom tags.

    Args:
        tags (dict): Dictionary of DICOM tags to be included in the email.
    Raises:
        Exception: If no valid receivers or SMTP configuration is provided.
    """
    
    uploader = USERNAME or "unbekannt"

    message_before_table = f"""
    <p style="font-family:Arial, sans-serif; font-size:14px;">
    Ein neuer Datensatz wurde von Nutzer <b>{uploader}</b> hochgeladen.
    </p>
    <p style="font-family:Arial, sans-serif; font-size:14px;">
    Die folgenden DICOM-Tags wurden erkannt:
    </p>
    """

    styled_table_html = format_tags_as_html(tags)

    email_body = f"""
    <html>
    <body>
        {message_before_table}
        {styled_table_html}
    </body>
    </html>
    """
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")
    combined_emails = f"{EMAIL},{EMAIL_RECEIVER}"
    receivers = [email.strip() for email in combined_emails.split(",") if email.strip()]
    if not receivers or (
        isinstance(receivers, list) and len(receivers) == 1 and receivers[0] == ""
    ):
        raise Exception("Cannot send email, no receivers defined!")

    smtp_host = os.getenv("SMTP_HOST", None)
    smtp_port = os.getenv("SMTP_PORT", 0)
    sender = os.getenv("EMAIL_ADDRESS_SENDER", None)
    smtp_username = os.getenv("SMTP_USERNAME", None)
    smtp_password = os.getenv("SMTP_PASSWORD", None)

    if smtp_port:
        smtp_port = int(smtp_port)
    else:
        smtp_port = 0

    if not smtp_host:
        raise Exception("Cannot send email, no smtp server defined!")

    if not sender:
        logger.warning(
            "No sender set. Some SMTP servers will not send data without a sender. If the send fails, this could be the reason."
        )

    msg = EmailMessage()
    msg["Subject"] = "Upload-Ergebnis: Neuer DICOM-Datensatz"
    msg["From"] = sender
    msg["To"] = ", ".join(receivers)

    msg.set_content(
        "Ein neuer DICOM-Datensatz wurde hochgeladen.\n"
        "Bitte öffnen Sie diese E-Mail in einem HTML-fähigen Client.",
    )

    msg.add_alternative(email_body, subtype="html")
    logger.info("Server info")
    logger.info(f"SMTP_HOST: {smtp_host}")
    logger.info(f"SMTP_PORT: {smtp_port}")
    logger.info(f"SMTP_USERNAME: {smtp_username}")
    logger.info(f"SENDER: {sender}")
    logger.info(f"RECEIVERS: {receivers}")
    # logger.info("Email content:")
    # logger.info(f"{msg}")'

    try:
        # Connect to the SMTP server and send the email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)

            server.send_message(msg)
            server.quit()
        logger.info("Successfully sent email")
    except smtplib.SMTPException as e:
        logger.info(e)
        logger.info("Error: unable to send email")
        exit(1)


if __name__ == "__main__":
    exit(start())