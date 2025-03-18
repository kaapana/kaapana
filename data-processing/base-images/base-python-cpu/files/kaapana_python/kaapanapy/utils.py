import os
from pathlib import Path
from os.path import exists, join
from glob import glob
from multiprocessing.pool import ThreadPool

from typing import Any, Callable, Optional

from kaapanapy.logger import get_logger

logger = get_logger(__name__)


class ConfigError(Exception):
    """Custom exception for configuration errors."""

    pass


def is_batch_mode(workflow_dir: Path, batch_name: Path) -> bool:
    """
    Determines if the input data is in batch mode by checking if the batch_name
    exists as a directory under workflow_dir and if there are subdirectories under batch_name.

    Args:
        workflow_dir (PathType): The path to the workflow directory.
        batch_name (PathType): The name of the batch directory to check within the workflow.

    Returns:
        bool: True if the data is in batch mode (i.e., if `batch_name` exists and contains subdirectories),
              False if it is in single mode (i.e., no subdirectories are found).
    """
    batch_dir = workflow_dir / batch_name

    if batch_dir.exists() and batch_dir.is_dir():
        # Check if there are subdirectories inside the batch directory
        batch_folders = [
            folder for folder in batch_dir.iterdir() if (batch_dir / folder).is_dir()
        ]

        if batch_folders:
            return True  # Multiple batch elements found, batch mode is confirmed

    # If no batch_name or no subdirectories in batch_name, it's single mode
    return False


def validate_directory(path: str, description: str) -> Path:
    """
    Validates that a directory exists. If the directory does not exist, logs an error and raises a ConfigError.

    Args:
        path (str): The path to the directory to validate.
        description (str): A description to be included in the error message if the directory does not exist.

    Returns:
        PathType: The validated path as a Path object.

    Raises:
        ConfigError: If the directory does not exist.
    """
    path = Path(path)
    if not path.exists():
        logger.error(f"{description} directory does not exist: {path}")
        raise ConfigError(f"{description} directory does not exist: {path}")
    return path


def get_required_env_var(var_name: str, default: Optional[Any] = None) -> Any:
    """
    Retrieves an environment variable, ensuring it exists. If the environment variable is missing,
    logs an error and raises a ConfigError.

    Args:
        var_name (str): The name of the environment variable to retrieve.
        default (Optional[Any]): The default value to return if the environment variable is not found. Defaults to None.

    Returns:
        Any: The value of the environment variable.

    Raises:
        ConfigError: If the environment variable does not exist and no default is provided.
    """
    value = os.getenv(var_name, default)
    if value is None:
        logger.error(f"Missing required environment variable: {var_name}")
        raise ConfigError(f"Missing required environment variable: {var_name}")
    return value


def process_batches(
    batch_dir: Path,
    operator_in_dir: Path,
    operator_out_dir: Path,
    processing_function: Callable,
    operator_get_ref_series_dir: Optional[Path] = None,
    thread_count: int = 3,
    **kwargs,
) -> None:
    """
    Processes batches of data by iterating through directories in `batch_dir` and calling the process_single function for each batch.

    Args:
        batch_dir (PathType): The path to the directory containing the batches.
        operator_in_dir (PathType): The path to the input directory for each batch.
        operator_out_dir (PathType): The path to the output directory for each batch.
        processing_function (ProcessingFunction): The function to be applied to each batch.
        operator_get_ref_series_dir (Optional[PathType]): The reference series input directory. Optional.
        thread_count (int): The number of threads to use for parallel processing. Defaults to 3.
        **kwargs: Additional keyword arguments to pass to the processing function.

    Returns:
        None: This function operates in place and does not return a value.
    """
    logger.info("Starting processing BATCHES ...")
    batch_dirs = sorted([f for f in glob(join("/", batch_dir, "*"))])

    for batch in batch_dirs:
        logger.info(f"Processing batch: {batch}")

        operator_out_dir.mkdir(exist_ok=True)
        process_single(
            base_dir=batch,
            operator_in_dir=operator_in_dir,
            operator_out_dir=operator_out_dir,
            operator_get_ref_series_dir=operator_get_ref_series_dir,
            processing_function=processing_function,
            thread_count=thread_count,
            **kwargs,
        )

        logger.info(f"Processing batch: {batch} done")
    logger.info(f"Processing batches done")


def process_single(
    base_dir: Path,
    operator_in_dir: Path,
    operator_out_dir: Path,
    processing_function: Callable,
    operator_get_ref_series_dir: Optional[Path] = None,
    thread_count: int = 3,
    **kwargs,
) -> None:
    """
    Processes a single batch of data, applying the processing function to the input directory and saving results to the output directory.

    Args:
        base_dir (PathType): The base directory where input and output directories are located.
        operator_in_dir (PathType): The input directory for the single batch.
        operator_out_dir (PathType): The output directory where results will be saved.
        processing_function (ProcessingFunction):
            - The function to process the data.
            - Arguments:
                - operator_in_dir
                - operator_out_dir
                - operator_get_ref_series_dir (Optional)
                - any extra parameters passed to the process_single as kwargs

            Example:
                ```python
                def generate_thumbnail(
                    operator_in_dir: Path,
                    operator_out_dir: Path,
                    operator_get_ref_series_dir: Path,
                    thumbnail_size: int,
                )
                ```

        operator_get_ref_series_dir (Optional[PathType]): The reference series input directory, optional.
        thread_count (int): The number of threads to use for parallel processing. Defaults to 3.
        **kwargs: Additional keyword arguments to pass to the processing function.

    Returns:
        None: This function operates in place and does not return a value.
    """
    queue = []
    logger.info("Starting processing SINGLE BATCH ...")

    if not exists(base_dir / operator_in_dir):
        logger.warning(f"Input-dir: {base_dir / operator_in_dir} does not exist!")
        logger.warning("# -> skipping")
        return

    (base_dir / operator_out_dir).mkdir(parents=True, exist_ok=True)

    task_args = {
        "processing_function": processing_function,
        "operator_in_dir": base_dir / operator_in_dir,
        "operator_out_dir": base_dir / operator_out_dir,
        **kwargs,
    }

    # Only add ref_in_dir if it's provided
    if operator_get_ref_series_dir:
        task_args["operator_get_ref_series_dir"] = (
            base_dir / operator_get_ref_series_dir
        )

    queue.append(task_args)

    with ThreadPool(thread_count) as threadpool:
        results = threadpool.imap_unordered(processing_function_wrapper, queue)
        for result, input_file in results:
            if result:
                logger.info(f"Done: {input_file}")

    logger.info("Single batch processing done.")


def processing_function_wrapper(args):
    """
    Wrapper to handle dictionary-based argument passing to the actual function.
    This ensures flexibility for different processing functions.
    kwargs arguments to process_single are unpacked into an arguments for the processing_function
    """
    processing_function = args.pop("processing_function")  # Extract the function
    return processing_function(**args)  # Unpack dictionary into function arguments
