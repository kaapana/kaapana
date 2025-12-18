import json
import logging
from pathlib import Path
from typing import List, Optional

from build_helper.utils import get_logger
from pydantic import BaseModel

logger = get_logger()


class Issue(BaseModel):
    component: str
    name: str
    msg: str
    level: str
    output: List[str]
    path: Optional[str] = None

    def log_self(self, logger: logging.Logger):
        """Logs this issue using the provided logger."""
        logger.warning("")
        logger.warning(f"{self.level} -> {self.component}:{self.name}")
        logger.warning(f"msg={self.msg}")
        logger.warning("\n".join(self.output))
        logger.warning("")
        logger.warning("-----------------------------------------------------------")


class IssueTracker:
    issues: List[Issue] = []
    exit_on_error: bool = False

    @classmethod
    def configure(cls, *, exit_on_error: bool = False):
        """Set whether the tracker should exit immediately on errors or fatal issues."""
        cls.exit_on_error = exit_on_error

    @classmethod
    def generate_issue(
        cls,
        component: str,
        name: str,
        msg: str,
        level: str,
        path: str | Path = "",
        output=None,
    ):
        """
        Create a BuildIssue instance and append it to the current ctx.build_state issues list.

        Logs error output if provided and emits a warning with the issue details in JSON format.

        Parameters:
            component (str): Component name related to the issue.
            name (str): Short descriptive name of the issue.
            level (str): Severity level (e.g., WARNING, ERROR, FATAL).
            msg (str): Detailed message describing the issue.
            path (str, optional): Filepath related to the issue.
            output (Any, optional): Optional command/process output to log.

        Raises:
            Exits the process if configured to exit on error or level is "FATAL".
        """
        log = []
        if output is not None:
            log = IssueTracker._make_log(output)
            logger.error("LOG:")
            logger.error(log)

        issue = Issue(
            component=component,
            name=name,
            msg=msg,
            level=level,
            path=str(path),
            output=log,
        )

        cls.issues.append(issue)
        logger.warning(json.dumps(issue.model_dump(), sort_keys=True))

        if cls.exit_on_error or level == "FATAL":
            exit(1)

        return issue

    @staticmethod
    def _make_log(output) -> list[str]:
        """
        Extracts and formats the last 100 lines of stdout and all stderr lines from a process output.

        Stdout lines are indexed from 0 upwards, and stderr lines are appended with an "ERROR:" prefix.

        Parameters:
            output (Any): An object expected to have `stdout` and `stderr` string attributes.

        Returns:
            list[str]: List of first 100 stdout lines and all stderr lines.
        """
        # Extract last 100 lines of stdout
        stdout_lines = output.stdout.splitlines()[-100:]

        # Non-empty stderr lines with "ERROR:" prefix
        stderr_lines = [
            f"ERROR: {line}" for line in output.stderr.splitlines() if line.strip()
        ]

        # Combine both lists
        combined_lines = stdout_lines + stderr_lines
        return combined_lines
