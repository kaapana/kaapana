import os
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def main() -> int:
    """Cleanup expired workflow data."""

    logging.info("Starting cleanup of expired workflow data")

    expired_raw = os.getenv("EXPIRED_PERIOD")
    if expired_raw is None:
        raise RuntimeError("EXPIRED_PERIOD must be set (in seconds)")

    try:
        expired_seconds = int(expired_raw)
    except ValueError:
        raise RuntimeError(
            f"Invalid EXPIRED_PERIOD value '{expired_raw}'; must be an integer (seconds)"
        )
    expired_period = timedelta(seconds=expired_seconds)

    workflow_dir = Path(os.getenv("WORKFLOW_DIR", "/kaapana/mounted/data/1"))
    data_dir = workflow_dir.parent

    logging.info("Expired period: %s", expired_period)
    logging.info("Working in: %s", data_dir)

    now = time.time()

    for run_dir in data_dir.iterdir():
        if not run_dir.is_dir():
            continue

        youngest_mtime = 0.0

        try:
            for path in run_dir.rglob("*"):
                try:
                    mtime = path.stat().st_mtime
                    youngest_mtime = max(youngest_mtime, mtime)
                except FileNotFoundError:
                    continue
        except PermissionError as exc:
            logging.warning("Skipping %s: %s", run_dir, exc)
            continue

        if youngest_mtime == 0:
            logging.info("Skipping empty directory %s", run_dir.name)
            continue

        age_seconds = now - youngest_mtime
        last_modified = datetime.fromtimestamp(youngest_mtime)

        logging.info(
            "Checking %s | Age: %s | Last modified: %s",
            run_dir.name,
            timedelta(seconds=age_seconds),
            last_modified.strftime("%Y-%m-%d %H:%M:%S"),
        )

        if age_seconds > expired_seconds:
            logging.info("Removing directory %s", run_dir)
            shutil.rmtree(run_dir, ignore_errors=True)

    logging.info("Cleanup of expired workflow data completed successfully")
    return 0


if __name__ == "__main__":
    exit(main())