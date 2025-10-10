import os
import requests
from requests.adapters import HTTPAdapter, Retry
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)


def download_file(
    url: str,
    dest_path: str,
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
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)

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

    if resume and os.path.exists(dest_path):
        existing_size = os.path.getsize(dest_path)
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

        progress = tqdm(
            total=total_size,
            initial=existing_size,
            unit="B",
            unit_scale=True,
            desc=f"Downloading {os.path.basename(dest_path)}",
            disable=not show_progress,
        )

        with open(dest_path, file_mode) as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    progress.update(len(chunk))
        progress.close()

    return dest_path
