import logging
import subprocess
from typing import Dict, List, Optional


class CommandHelper:
    @staticmethod
    def run(
        command: List[str] | str,
        *,
        timeout: int = 30,
        shell: bool = False,
        env: Optional[Dict[str, str]] = None,
        log_command: bool = True,
        exit_on_error: bool = False,
        context: Optional[str] = None,
        hints: Optional[List[str]] = None,
        logger: logging.Logger,
    ) -> subprocess.CompletedProcess:
        if log_command:
            logger.debug(f"{'[' + context + '] ' if context else ''}Running: {command}")

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                shell=shell,
                env=env,
            )
        except Exception as e:
            logger.error(
                f"{'[' + context + '] ' if context else ''}Command failed: {e}"
            )
            if hints:
                for hint in hints:
                    logger.error(f"hint: {hint}")
            if exit_on_error:
                exit(1)
            raise

        if result.returncode != 0:
            logger.error(f"{'[' + context + '] ' if context else ''}Command failed")
            logger.error(f"stdout: {result.stdout.strip()}")
            logger.error(f"stderr: {result.stderr.strip()}")
            if hints:
                for hint in hints:
                    logger.error(f"hint: {hint}")
            if exit_on_error:
                exit(1)

        return result
