#!/usr/bin/env python3
import argparse
import logging
from build_helper.security_utils import TrivyUtils
from subprocess import PIPE, run, DEVNULL
from build_helper.build_utils import BuildUtils
from os.path import join, dirname, exists
import os
import yaml
import signal

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.INFO)

c_format = logging.Formatter("%(levelname)s - %(message)s")
c_handler.setFormatter(c_format)

logger.addHandler(c_handler)

BuildUtils.init()
BuildUtils.exit_on_error = False
BuildUtils.logger = logger

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--sbom",
        dest="sbom",
        action="store_true",
        default=False,
        help="Create SBOMs",
    )
    parser.add_argument(
        "-v",
        "--vuln",
        action="store_true",
        dest="vuln",
        default=False,
        help="Create vulnerability reports",
    )
    parser.add_argument(
        "-t",
        "--tag",
        dest="tag",
        default=None,
        required=False,
        help="Plattform version: e.g.: 0.1.3-591-g6426ef53",
    )
    parser.add_argument(
        "-n",
        "--num-parallel-processes",
        dest="num_parallel_processes",
        default=2,
        required=False,
        help="Number of parallel processes",
    )
    args = parser.parse_args()

    sbom = args.sbom
    vuln = args.vuln
    tag = args.tag

    kaapana_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_dir = join(dirname(dirname(os.path.realpath(__file__))), "build")
    config_filepath = os.path.join(kaapana_dir, "build-scripts", "build-config.yaml")
    assert exists(config_filepath)

    with open(config_filepath, "r") as stream:
        try:
            configuration = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logger.info(exc)

    BuildUtils.kaapana_dir = kaapana_dir
    BuildUtils.build_dir = build_dir
    BuildUtils.parallel_processes = int(args.num_parallel_processes)
    BuildUtils.create_sboms = sbom
    BuildUtils.vulnerability_scan = vuln

    trivy_utils = TrivyUtils()

    def handler(signum, frame):
        BuildUtils.logger.info("Exiting...")

        trivy_utils.kill_flag = True

        with trivy_utils.semaphore_threadpool:
            if trivy_utils.threadpool is not None:
                trivy_utils.threadpool.terminate()
                trivy_utils.threadpool = None
            
        trivy_utils.error_clean_up()

        if BuildUtils.create_sboms:
            trivy_utils.safe_sboms()
        if BuildUtils.vulnerability_scan:
            trivy_utils.safe_vulnerability_reports()

        exit(1)

    signal.signal(signal.SIGTSTP, handler)

    if tag == None:
        logger.error("No tag provided!")
        exit(1)
    else:
        logger.info("Tag: {}".format(tag))
        list_of_containers = []
        # Get all containers with tag
        command = "docker images | grep {} | awk '{{print $1}}'".format(tag)
        result = run(
            command, shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                list_of_containers.append(line + ":" + tag)

        # Get all containers starting with "local-only"
        command = "docker images | grep local-only | awk '{{print $1}}'"
        result = run(
            command, shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                list_of_containers.append(line + ":latest")

        logger.info("")
        logger.info("List of containers:")
        logger.info("")
        for container in list_of_containers:
            logger.info("Container: {}".format(container))

    if sbom:
        logger.info("Creating SBOMs...")
        trivy_utils.create_sboms(list_of_containers)
        logger.info("Done.")

    if vuln:
        logger.info("Creating vulnerability reports...")
        trivy_utils.create_vulnerability_reports(list_of_containers)
        logger.info("Done.")
