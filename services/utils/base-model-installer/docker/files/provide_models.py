from pathlib import Path
import os
import json
import logging
import requests
from requests.adapters import HTTPAdapter, Retry
import zipfile
import sys
from multiprocessing.pool import ThreadPool
from functools import partial
import tqdm
import argparse

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)


def download_file(
    url: str,
    dest_path: Path,
    chunk_size: int = 8192,
    show_progress: bool = True,
    max_retries: int = 5,
    timeout: int = 7200,
    resume: bool = True,
):
    """
    Robust file downloader using requests with streaming, retries, and resume support.

    Args:
        url (str): URL to download from.
        dest_path (str): Destination path for the file.
        chunk_size (int, optional): Chunk size in bytes. Default 8KB.
        show_progress (bool, optional): Display tqdm progress bar. Default True.
        max_retries (int, optional): Number of automatic retries for transient errors.
        timeout (int, optional): Timeout (in seconds) for each request.
        resume (bool, optional): Try to resume partial downloads. Default True.

    Raises:
        requests.exceptions.RequestException: If the download fails permanently.
        IOError: If writing to file fails.

    Returns:
        str: Path to the downloaded file.
    """

    # Ensure destination directory exists
    dest_path.absolute().parent.mkdir(exist_ok=True)

    # Session with retry strategy
    session = requests.Session()
    retries = Retry(
        total=max_retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))

    # Determine if we can resume
    resume_header = {}
    file_mode = "wb"
    existing_size = 0

    if resume and dest_path.exists():
        existing_size = dest_path.stat().st_size
        resume_header = {"Range": f"bytes={existing_size}-"}
        file_mode = "ab"

    with session.get(
        url, stream=True, headers=resume_header, timeout=timeout
    ) as response:
        # If resuming, handle HTTP 206 (partial content)
        if response.status_code == 416:
            logger.info("Download already complete.")
            return dest_path
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        total_size += existing_size

        progress = tqdm.tqdm(
            total=total_size,
            initial=existing_size,
            unit="B",
            unit_scale=True,
            desc=f"Downloading {dest_path.name}",
            disable=not show_progress,
        )

        with open(dest_path, file_mode) as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    progress.update(len(chunk))
        progress.close()

    return dest_path


def download_and_extract(
    task_id: str,
    model_download_link: str,
    download_dir: Path,
    extract_model: bool = False,
    extraction_dir: Path = Path("/models"),
):
    model_zip_file = Path(download_dir, f"{task_id}.zip")
    if not model_zip_file.is_file():
        logger.debug(f"Download model for {task_id} from {model_download_link}")
        try:
            download_file(url=model_download_link, dest_path=model_zip_file)
        except requests.exceptions.RequestException:
            logger.error(
                f"Failed to download model for {task_id=} from {model_download_link}"
            )
            return
    else:
        logger.debug(f"Model archive for {task_id=} already exists -> Skip download!")

    if extract_model:
        logger.debug(f"Extract file {model_zip_file} into {extraction_dir}")
        try:
            with zipfile.ZipFile(model_zip_file, "r") as zip_ref:
                zip_ref.extractall(extraction_dir)
        except Exception as e:
            logger.error(f"Failed to extract model for {task_id=}! Error: {str(e)}")
            if model_zip_file.is_file():
                model_zip_file.unlink()
            return

    return task_id


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--all", "-a", default="false", action="store", choices=["true", "false"]
    )
    parser.add_argument("--task-ids", default=os.getenv("TASK_IDS", ""))
    parser.add_argument("--download-dir", default="/kaapana/app/models")

    parser.add_argument("--extract-models", "-e", action="store_true")
    parser.add_argument(
        "--extraction-dir", "-ed", default=os.getenv("MODEL_DIR", "/models")
    )

    return parser.parse_args()


if __name__ == "__main__":
    logger.info("Start main process.")

    args = parse_arguments()

    with open(Path("/model_lookup.json"), "r") as f:
        model_lookup = json.load(f)

    if args.all.lower() == "true":
        task_ids = model_lookup.keys()
    else:
        task_ids = args.task_ids.split(",")

    if len(task_ids) == 0:
        logger.warning(f"No task_ids specified!")
        sys.exit(0)

    Path(args.download_dir).mkdir(exist_ok=True)
    if args.extract_models:
        Path(args.extraction_dir).mkdir(exist_ok=True)

    worker_args = []

    for task_id in task_ids:
        try:
            model_info = model_lookup[task_id]
            model_download_link = model_info.get("download_link")
        except KeyError:
            logger.error(f"No information found in the container for {task_id=}")
            continue

        model_already_provided = (
            Path(args.extraction_dir, task_id, model_info.get("check_file")).exists()
            if model_info.get("check_file")
            else Path(args.extraction_dir, task_id).exists()
        )

        if model_already_provided:
            logger.info(f"Model for {task_id} already already exists.")
        else:
            worker_args = [
                {"task_id": task_id, "model_download_link": model_download_link}
            ]

    worker = partial(
        download_and_extract,
        download_dir=Path(args.download_dir),
        extract_model=args.extract_models,
        extraction_dir=Path(args.extraction_dir),
    )
    with ThreadPool(max(len(task_ids), 4)) as threadpool:
        results = threadpool.imap_unordered(lambda kw: worker(**kw), worker_args)
        for task_id in results:
            if task_id:
                logger.info(f"Model for {task_id=} provided successfully!")
