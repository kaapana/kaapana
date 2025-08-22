import json
import logging
from time import time
from typing import Dict, List, Optional

from build_helper.build_config import BuildConfig
from build_helper.security_utils import TrivyUtils
from pydantic import BaseModel, Field


class BuildIssue(BaseModel):
    component: str
    name: str
    msg: str
    level: str
    path: Optional[str] = None
    output: Optional[str] = None


class BuildProgress(BaseModel):
    started_at: float
    finished_at: Optional[float] = None
    duration: Optional[float] = None
    built_containers: Dict[str, str] = Field(default_factory=dict)  # tag -> status
    build_issues: List[BuildIssue] = Field(default_factory=list)
    base_images_used: Dict[str, List[str]] = Field(
        default_factory=dict
    )  # base_tag -> container_tags


class BuildUtils:
    config: BuildConfig
    logger: logging.Logger
    trivy_utils: Optional[TrivyUtils] = None
    progress: Optional[BuildProgress] = None

    @classmethod
    def init(
        cls,
        config: BuildConfig,
        logger: logging.Logger,
        progress: Optional[BuildProgress] = None,
    ):
        cls.config = config
        cls.logger = logger
        cls.progress = progress
        cls.issues_list = []
        cls.base_images_used = {}

        if (
            config.vulnerability_scan
            or config.create_sboms
            or config.configuration_check
        ):
            logger.info("Initializing Trivy.")
            cls.trivy_utils = TrivyUtils(tag="no_tag_yet")
        else:
            cls.trivy_utils = None

        cls.logger.debug("BuildUtils initialized")

    @staticmethod
    def generate_issue(component, name, level, msg, path="", output=None):
        log = ""
        if output != None:
            log = BuildUtils.make_log(output)
            BuildUtils.logger.error("LOG:")
            BuildUtils.logger.error(log)

        issue = {
            "component": component,
            "name": name,
            "filepath": path,
            "level": level,
            "msg": msg,
            "log": log,
            "timestamp": BuildUtils.get_timestamp(),
        }
        BuildUtils.issues_list.append(issue)
        BuildUtils.logger.warning(json.dumps(issue, indent=4, sort_keys=False))

        if BuildUtils.config.exit_on_error or level == "FATAL":
            exit(1)

    @staticmethod
    def make_log(output):
        std_out = output.stdout.split("\n")[-100:]
        log = {}
        len_std = len(std_out)
        for i in range(0, len_std):
            log[i] = std_out[i]
        std_err = output.stderr.split("\n")
        for err in std_err:
            if err != "":
                len_std += 1
                log[len_std] = f"ERROR: {err}"
        return log

    @staticmethod
    def get_timestamp():
        return str(int(time() * 1000))
