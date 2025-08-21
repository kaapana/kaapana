import logging
import os
import subprocess
import sys
import time
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    """
    Simple drop-in replacement for kaapanapy.logger.get_logger.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:  # avoid adding handlers twice
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger


logger = get_logger(__name__)


def main():
    fast_data_env = os.getenv("FAST_DATA_DIR")
    if not fast_data_env:
        logger.error("No fast_data_dir specified")
        exit(1)

    fast_data_dir = Path(fast_data_env)
    if not fast_data_dir.exists():
        logger.error(f"fast_data_dir doees not exists: {fast_data_dir}")
        exit(1)

    slow_data_env = os.getenv("SLOW_DATA_DIR")
    if not slow_data_env:
        logger.error("No slow_data_dir specified")
        exit(1)
    slow_data_dir = Path(slow_data_env)

    if not Path(slow_data_dir).exists():
        logger.error(f"slow_data_dir doees not exists: {slow_data_dir}")
        exit(1)

    data_state_version = os.getenv("DATA_STATE_VERSION")
    if not data_state_version:
        logger.error("No data state version")
        exit(1)
    old_version = ".".join(data_state_version.split(".")[:2])

    target_platform_version = os.getenv("TARGET_PLATFORM_VERSION")
    if not target_platform_version:
        logger.error("No target platform version")
        exit(1)
    new_version = ".".join(target_platform_version.split(".")[:2])

    if data_state_version == "none":
        logger.info(
            f"No data state version found. Assuming new release of version: {target_platform_version}"
        )
        fast_data_dir.mkdir(parents=True, exist_ok=True)
        (fast_data_dir / "version").write_text(target_platform_version)
        exit(0)

    migration_scripts_dir = Path("/kaapana/app/")
    if not migration_scripts_dir.exists():
        logger.error("No migration scripts dir exists: migration_scripts_dir")
        exit(1)

    logger.info(migration_scripts_dir)
    logger.info(fast_data_dir)
    logger.info(slow_data_dir)
    logger.info(old_version)
    logger.info(new_version)

    major_old, minor_old = old_version.split(".")
    major_new, minor_new = new_version.split(".")

    migration_script_path = (
        migration_scripts_dir
        / f"migration-{major_old}.{minor_old}.x-{major_new}.{minor_new}.x.sh"
    )
    if not migration_script_path.exists():
        logger.error(f"No migration script found: {migration_script_path}")
        exit(1)

    try:
        logger.info(f"Running migration script: {migration_script_path}")
        # Make sure the script is executable
        migration_script_path.chmod(0o755)

        result = subprocess.run(
            [str(migration_script_path), fast_data_dir, slow_data_dir],
            check=True,  # Raise CalledProcessError on failure
            capture_output=True,
            text=True,
        )

        logger.info(
            f"Migration script completed successfully.\nOutput:\n{result.stdout}"
        )
        if result.stderr:
            logger.warning(f"Migration script warnings/errors:\n{result.stderr}")

        logger.info("Overwrite version file with the new version")
        (fast_data_dir / "version").write_text(new_version)

    except subprocess.CalledProcessError as e:
        logger.error(
            f"Migration script failed with exit code {e.returncode}\nOutput:\n{e.output}\nError:\n{e.stderr}"
        )
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
