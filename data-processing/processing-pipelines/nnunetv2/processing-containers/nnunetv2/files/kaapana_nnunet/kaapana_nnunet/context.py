"""Everything a step needs from the Kaapana pod: form values, project bucket, scratch space, S3, logging."""

import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
from collections import deque
from pathlib import Path
from typing import Any, Optional

from kaapana_nnunet import layout
from kaapana_nnunet.store import S3Store

logger = logging.getLogger("kaapana_nnunet")


class StepError(Exception):
    """An error the user can fix. Printed without a traceback."""


def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)


class Context:
    def __init__(self, conf: Optional[dict] = None):
        self.workflow_dir = Path(os.environ.get("WORKFLOW_DIR", "/tmp/nnunet-run"))
        self.conf = conf if conf is not None else self._load_conf()
        self.form = self.conf.get("workflow_form", {})
        self.project = self.conf.get("project_form", {})
        out_dir = os.environ.get("OPERATOR_OUT_DIR", "nnunet")
        self.scratch = self.workflow_dir / out_dir
        self.scratch.mkdir(parents=True, exist_ok=True)
        self.run_id = os.environ.get("RUN_ID", "local")
        self._store = None

    def _load_conf(self) -> dict:
        path = self.workflow_dir / "conf" / "conf.json"
        if not path.is_file():
            return {}
        return json.loads(path.read_text())

    # ---------- form ----------

    def get(self, key: str, default: Any = None) -> Any:
        """A form value; fields of the collapsed "advanced" section are found as well."""
        for source in (self.form, self.form.get("advanced") or {}):
            value = source.get(key)
            if value not in (None, "", []):
                return value
        return default

    advanced = get

    def flag(self, key: str, default: bool = False) -> bool:
        value = self.get(key, default)
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)

    def require(self, key: str) -> Any:
        value = self.get(key)
        if value is None:
            raise StepError(f"The form field '{key}' is required.")
        return value

    def selection(self) -> str:
        """The item picked in the form's dropdown (installed_models task_ids)."""
        value = self.get("task_ids")
        if not value:
            raise StepError("Nothing selected. Pick an entry in the first dropdown of the form.")
        return value

    @property
    def identifiers(self) -> list[str]:
        return list((self.conf.get("data_form") or {}).get("identifiers") or [])

    # ---------- S3 ----------

    @property
    def bucket(self) -> str:
        bucket = self.project.get("s3_bucket") or os.environ.get("NNUNET_S3_BUCKET")
        if not bucket:
            raise StepError("No project bucket in the workflow configuration (project_form.s3_bucket).")
        return bucket

    @property
    def store(self) -> S3Store:
        if self._store is None:
            from kaapana_client.helper.HelperMinioSessionManager import HelperMinioSessionManager

            session = HelperMinioSessionManager()
            self._store = S3Store(session.get_client, self.bucket)
        return self._store

    # ---------- pod folders ----------

    def prepare(self) -> dict:
        env = layout.prepare_pod_dirs(self.scratch)
        logger.info("nnU-Net folders: %s", env)
        return env

    def cleanup(self):
        if os.environ.get("NNUNET_KEEP_SCRATCH", "").lower() in ("1", "true"):
            return
        shutil.rmtree(self.scratch, ignore_errors=True)


def provenance(ctx: Context, **extra) -> dict:
    """Recorded in every marker: which code produced the data, from which run, with which settings."""
    return {
        "nnunet_commit": os.environ.get("NNUNET_COMMIT", "unknown"),
        "nnunet_code": os.environ.get("NNUNET_CODE_SNAPSHOT", "built-in"),
        "run_id": ctx.run_id,
        "dag_id": os.environ.get("DAG_ID"),
        "workflow_form": ctx.form,
        **extra,
    }


def run_nnunet(args: list[str], hint: str = "", env: Optional[dict] = None) -> str:
    """Run an nnU-Net command, stream its output, raise StepError with the tail of the output on failure."""
    printable = " ".join(shlex.quote(a) for a in args)
    logger.info("running: %s", printable)
    tail = deque(maxlen=60)
    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ, **(env or {})},
    )
    for line in proc.stdout:
        sys.stdout.write(line)
        tail.append(line.rstrip())
    proc.wait()
    if proc.returncode != 0:
        msg = [f"nnU-Net failed (exit code {proc.returncode}): {printable}", "", "Last output:", *tail]
        if hint:
            msg += ["", hint]
        raise StepError("\n".join(msg))
    return "\n".join(tail)


def sync_dropdowns(ctx: Context):
    """Rebuild the form dropdowns (backend installed_models) of this project from the S3 markers."""
    from kaapana_nnunet import catalog

    try:
        catalog.sync(ctx)
    except Exception as e:  # dropdowns are a convenience, never fail a finished step for them
        logger.warning("could not refresh the workflow dropdowns: %s", e)


def main(step):
    """Entry point wrapper: user errors end with a readable message and exit code 1."""
    setup_logging()
    ctx = Context()
    try:
        step(ctx)
    except StepError as e:
        bar = "=" * 80
        print(f"\n{bar}\nERROR\n{bar}\n{e}\n{bar}\n", flush=True)
        sys.exit(1)
    finally:
        ctx.cleanup()
