import os
from glob import glob
from pathlib import Path
from shutil import which
from typing import List

from alive_progress import alive_bar
from build_helper_v2.core.build_state import BuildState
from build_helper_v2.core.container import Container
from build_helper_v2.models.build_config import BuildConfig
from build_helper_v2.services.issue_tracker import IssueTracker
from build_helper_v2.utils.command_helper import CommandHelper
from build_helper_v2.utils.logger import get_logger

logger = get_logger()


class Trivy:
    pass

    @classmethod
    def sbom(cls):
        pass
    
    @classmethod
    def vulnerability_scan(cls):
        pass
    
    