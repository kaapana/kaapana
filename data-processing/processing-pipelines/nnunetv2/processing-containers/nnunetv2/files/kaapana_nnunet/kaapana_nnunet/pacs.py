"""Sending DICOM back to Kaapana: through its DICOM receiver (CTP), which indexes it and adds it to a dataset."""

import logging
import os
import re
import subprocess

from kaapana_nnunet.context import Context, StepError

logger = logging.getLogger(__name__)

AETITLE_RE = re.compile(r"^[A-Za-z0-9._-]{1,13}$")


def check_aetitle(aetitle: str):
    """The Kaapana dataset name travels as calling AE title kp-<name>: at most 16 characters."""
    if not AETITLE_RE.match(aetitle):
        raise StepError(
            f"Result dataset '{aetitle}' is not usable: 1-13 characters, letters, digits, '.', '_' or '-'."
        )


def send_to_pacs(ctx: Context, folder, aetitle: str):
    """dcmsend to Kaapana's DICOM receiver (CTP): indexed and assigned to this project like any upload."""
    host = os.environ.get("PACS_HOST")
    if not host:
        from kaapana_client.settings import KaapanaSettings

        host = f"ctp-dicom-service.{KaapanaSettings().services_namespace}.svc"
    project = ctx.project.get("short_id") or "admin"
    args = ["dcmsend", "-v", host, os.environ.get("PACS_PORT", "11112"), "-aet", f"kp-{aetitle}"]
    args += ["-aec", f"kp-{project}", "--scan-directories", "--recurse", "--no-halt", str(folder)]
    for attempt in range(1, 6):
        out = subprocess.run(args, capture_output=True, text=True, timeout=600)
        if out.returncode == 0 and "with status SUCCESS" in out.stdout + out.stderr:
            return
        logger.warning("dcmsend attempt %d failed:\n%s%s", attempt, out.stdout, out.stderr)
    raise StepError("Sending the segmentations to the PACS failed (dcmsend), see the log above.")
