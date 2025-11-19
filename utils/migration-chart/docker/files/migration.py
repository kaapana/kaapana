import logging
import os
import re
import subprocess
import sys
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


def autodetect_version(extensions_dir: Path) -> str:
    logger.info(
        "Trying to automatically detect version using kaapana-platform-chart in %s",
        extensions_dir,
    )

    candidates = list(extensions_dir.glob("kaapana-platform-chart-*.tgz"))
    if not candidates:
        raise FileNotFoundError(
            f"No kaapana-platform-chart-*.tgz found in {extensions_dir}. Please create version file `sudo nano version` and add <version> (e.g., 0.4.1) inside the <fast_data_dir> and re-run"
        )

    if len(candidates) > 1:
        logger.warning(
            "Multiple kaapana-platform-chart files found, taking the first one: %s",
            candidates[0],
        )

    filename = candidates[0].name
    # Extract version between "kaapana-platform-chart-" and ".tgz"
    m = re.search(
        r"kaapana-platform-chart-([0-9]+\.[0-9]+(?:\.[0-9]+)?(?:-[^-]+)?)\.tgz",
        filename,
    )
    if not m:
        raise ValueError(f"Could not parse version from {filename}")

    version = m.group(1)
    logger.info("Detected platform version: %s", version)
    return version


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

    from_version = os.getenv("FROM_VERSION")
    if not from_version:
        logger.error("No from_version")
        exit(1)

    to_version = os.getenv("TO_VERSION")
    if not to_version:
        logger.error("No to_version")
        exit(1)

    if from_version == "fresh":
        logger.info("Assuming fresh installation")
        fast_data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Creating version file imprint: {to_version}")
        (fast_data_dir / "version").write_text(to_version)
        exit(0)

    if from_version == "autodetect":
        from_version = autodetect_version(fast_data_dir / "extensions")

    migration_scripts_dir = Path("/kaapana/app/")
    if not migration_scripts_dir.exists():
        logger.error(f"No migration scripts dir exists: {migration_scripts_dir}")
        exit(1)

    logger.info(migration_scripts_dir)
    logger.info(fast_data_dir)
    logger.info(slow_data_dir)
    logger.info(from_version)
    logger.info(to_version)

    major_from, minor_from, _ = map(int, from_version.split("-")[0].split("."))
    major_to, minor_to, _ = map(int, to_version.split("-")[0].split("."))

    if major_from != major_to:
        logger.error("Major version migration not supported yet")
        exit(1)

    version_chain = []

    minor_current = minor_from
    logger.info("Generating migration chain")
    while minor_current < minor_to:
        version_chain.append((major_from, minor_current, major_to, minor_current + 1))
        minor_current += 1

    logger.info("Migration chain generated. Validatin migration chain")
    for major_from, minor_from, major_to, minor_to in version_chain:
        migration_script_path = (
            migration_scripts_dir
            / f"migration-{major_from}.{minor_from}.x-{major_to}.{minor_to}.x.sh"
        )
        if not migration_script_path.exists():
            logger.error(f"No migration script found: {migration_script_path}")
            logger.error("No migration performed.")
            exit(1)

    for major_from, minor_from, major_to, minor_to in version_chain:
        migration_script_path = (
            migration_scripts_dir
            / f"migration-{major_from}.{minor_from}.x-{major_to}.{minor_to}.x.sh"
        )
        try:
            logger.info(f"Running migration script: {migration_script_path}")
            migration_script_path.chmod(0o755)

            result = subprocess.run(
                [str(migration_script_path), str(fast_data_dir), str(slow_data_dir)],
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
            (fast_data_dir / "version").write_text(f"{major_to}.{minor_to}")

        except subprocess.CalledProcessError as e:
            logger.error(
                f"Migration script failed with exit code {e.returncode}\nOutput:\n{e.output}\nError:\n{e.stderr}"
            )
            sys.exit(e.returncode)

        logger.info(f"Output:\n{result.stdout}")
        if result.stderr:
            logger.info(f"Warnings/errors:\n{result.stderr}")

        logger.info("Check version file is the newest version")
        minor_final = (fast_data_dir / "version").read_text().split(".")[1]
        assert int(minor_final) == int(
            minor_to
        ), f"Not finished on the same version!: {minor_to=} -> {minor_final=}"


if __name__ == "__main__":
    main()
