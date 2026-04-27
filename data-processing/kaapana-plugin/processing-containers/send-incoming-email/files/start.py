import os
import smtplib
import mimetypes
import logging
from pathlib import Path
from email.message import EmailMessage

import pydicom

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def dicom_value(ds, keyword, default=""):
    elem = ds.get(keyword, None)
    if elem is None:
        return default
    val = elem.value if hasattr(elem, "value") else elem
    return str(val) if val is not None else default


def format_tags_as_html(tags: dict) -> str:
    rows = []
    for key, value in tags.items():
        display_value = value if value else "—"
        rows.append(
            f"""
            <tr>
                <td style="padding:6px 10px; font-weight:600; background:#f5f5f5;">
                    {key}
                </td>
                <td style="padding:6px 10px;">
                    {display_value}
                </td>
            </tr>
            """
        )

    return f"""
    <table border="1" cellspacing="0" cellpadding="0"
           style="border-collapse:collapse; font-family:Arial, sans-serif; font-size:13px; margin-bottom:12px;">
        {''.join(rows)}
    </table>
    """


def attach_files(msg: EmailMessage, files: list[Path]):
    for file in files:
        ctype, encoding = mimetypes.guess_type(file)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"

        maintype, subtype = ctype.split("/", 1)

        with open(file, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=file.name,
            )


def send_via_smtp(msg: EmailMessage):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 0))
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    if not smtp_host:
        raise RuntimeError("SMTP_HOST not configured")

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)
        server.send_message(msg)

    logger.info("Email successfully sent")


def get_receivers() -> list[str]:
    email_receiver = os.getenv("EMAIL_RECEIVER", "")
    receivers = [e.strip() for e in email_receiver.split(",") if e.strip()]
    if not receivers:
        raise RuntimeError("No email receivers configured")
    return receivers


# ---------------------------------------------------------------------
# Main email sender (ONE email per upload)
# ---------------------------------------------------------------------

def send_upload_notification(tag_blocks: list[dict], attachments: list[Path]):
    uploader = os.getenv("USERNAME", "unbekannt")

    header_html = f"""
    <p style="font-family:Arial, sans-serif; font-size:14px;">
        Ein neuer Upload wurde von Nutzer <b>{uploader}</b> durchgeführt.
    </p>
    """

    tables_html = ""
    for idx, tags in enumerate(tag_blocks, start=1):
        tables_html += f"""
        <h4 style="font-family:Arial, sans-serif;">
            Datensatz {idx}
        </h4>
        {format_tags_as_html(tags)}
        """

    body_html = f"""
    <html>
    <body>
        {header_html}
        {tables_html}
    </body>
    </html>
    """

    msg = EmailMessage()
    msg["Subject"] = "Upload-Ergebnis: Neuer DICOM-Upload"
    msg["From"] = os.getenv("EMAIL_ADDRESS_SENDER")
    msg["To"] = ", ".join(get_receivers())

    msg.set_content(
        "Ein neuer Upload wurde durchgeführt. "
        "Bitte öffnen Sie diese E-Mail in einem HTML-fähigen Client."
    )

    msg.add_alternative(body_html, subtype="html")

    if attachments:
        attach_files(msg, attachments)

    send_via_smtp(msg)


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

def start():
    send_dir = Path(
        "/", os.environ["WORKFLOW_DIR"], os.environ["OPERATOR_IN_DIR"]
    )

    logger.info(f"Processing upload root: {send_dir}")

    all_tag_blocks: list[dict] = []
    all_pdfs: list[Path] = []

    for root, _, _ in os.walk(send_dir):
        current_dir = Path(root)

        # Collect PDFs (global)
        all_pdfs.extend(
            [p for p in current_dir.glob("*.pdf") if p.is_file()]
        )

        # Collect DICOMs (per folder)
        dicom_files = [
            f for f in current_dir.iterdir()
            if f.is_file() and pydicom.misc.is_dicom(f)
        ]

        if not dicom_files:
            continue

        try:
            ds = pydicom.dcmread(dicom_files[0])

            tags = {
                "PatientID": dicom_value(ds, "PatientID"),
                "PatientName": dicom_value(ds, "PatientName"),
                "AccessionNumber": dicom_value(ds, "AccessionNumber"),
                "StudyDescription": dicom_value(ds, "StudyDescription"),
                "StudyDate": dicom_value(ds, "StudyDate"),
                "InstitutionName": dicom_value(ds, "InstitutionName"),
            }

            all_tag_blocks.append(tags)

        except Exception as e:
            logger.error(f"Error reading DICOM file {dicom_files[0]}: {e}")

    logger.info(
        "Upload scan finished: %d DICOM dataset(s), %d PDF(s) found",
        len(all_tag_blocks),
        len(all_pdfs),
    )

    if not all_tag_blocks and not all_pdfs:
        logger.info("Nothing to report — no email sent")
        return

    send_upload_notification(
        tag_blocks=all_tag_blocks,
        attachments=all_pdfs,
    )


# ---------------------------------------------------------------------
# Optional: allow script execution
# ---------------------------------------------------------------------

if __name__ == "__main__":
    start()
