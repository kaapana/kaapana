import os
import subprocess

from build_cli.build.build_config import BuildConfig
from build_cli.container.container import Container
from build_cli.container.container_helper import BUILDX_BUILDER_NAME
from build_cli.utils.git_utils import GitUtils


def run_bake(containers: set[Container], build_config: BuildConfig):

    version, branch, commit, timestamp = GitUtils.get_repo_info(
        build_config.kaapana_dir
    )

    command = [
        build_config.container_engine,
        "buildx",
        "bake",
        "-f",
        "bake-kaapana.hcl",
        "--builder",
        BUILDX_BUILDER_NAME,
    ]
    command.extend([container.image_name for container in containers])
    process = subprocess.run(
        command,
        env={
            **os.environ,
            "REGISTRY": build_config.default_registry,
            "TAG": version,
            "CACHE_TO": str(build_config.cache_to),
            "CACHE_FROM": str(build_config.cache_from),
            "CACHE_REGISTRY": build_config.cache_registry
            or build_config.default_registry,
            "BUILD_ONLY": str(build_config.build_only),
        },
    )
    process.check_returncode()
