#!/usr/bin/env python3
import os
from subprocess import PIPE, run, DEVNULL
from build_helper.build_utils import BuildUtils
import json
from shutil import which
import threading
from multiprocessing.pool import ThreadPool
from alive_progress import alive_bar


suite_tag = "security"
skip_commands = {
    "otsus-method": [
        [
            "--skip-files",
            "usr/local/lib/python3.9/site-packages/nibabel/tests/data/Phantom_EPI_3mm_sag_15RL_SENSE_11_1.PAR",
        ]
    ],
}

# Class containing security related helper functions
# Using Trivy to create SBOMS and check for vulnerabilities
class TrivyUtils:

    sboms = {}
    vulnerability_reports = {}
    compressed_vulnerability_reports = {}
    compressed_dockerfile_report = {}
    trivy_image = "0.38.3"
    timeout = 10000
    threadpool = None
    list_of_running_containers = []
    kill_flag = False

    def __init__(self):
        # Check if trivy is installed
        if which("trivy") is None:
            BuildUtils.logger.error(
                "Trivy is not installed, please visit https://aquasecurity.github.io/trivy/v0.38/getting-started/installation/ for installation instructions. You must install Trivy version 0.38.1, higher is not supported yet."
            )
            BuildUtils.generate_issue(
                component=suite_tag,
                name="Check if Trivy is installed",
                msg="Trivy is not installed",
                level="ERROR",
            )
        # Check if severity level is set (enable all vulnerabily severity levels if not set)
        if (
            BuildUtils.vulnerability_severity_level == ""
            or BuildUtils.vulnerability_severity_level == None
        ):
            BuildUtils.vulnerability_severity_level = "CRITICAL,HIGH,MEDIUM,LOW,UNKNOWN"
        # Check if vulnerability_severity_levels are in the allowed values
        elif not all(
            x in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
            for x in BuildUtils.vulnerability_severity_level.split(",")
        ):
            BuildUtils.logger.warning(
                f"Invalid severity level set in vulnerability_severity_level: {BuildUtils.vulnerability_severity_level}. Allowed values are: CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN"
            )
            BuildUtils.generate_issue(
                component=suite_tag,
                name="Check if vulnerability_severity_level is set correctly",
                msg="Invalid severity level set in vulnerability_severity_level",
                level="ERROR",
            )

        self.semaphore_sboms = threading.Lock()
        self.semaphore_vulnerability_reports = threading.Lock()
        self.semaphore_compressed_dockerfile_report = threading.Lock()
        self.semaphore_running_containers = threading.Lock()

        self.threadpool = ThreadPool(BuildUtils.parallel_processes)

    def check_if_image_exists(self, image):
        command = ["docker", "image", "inspect", image]

        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=self.timeout,
        )

        if output.returncode != 0:
            return False
        else:
            return True

    # Function to create SBOM for a given image
    def create_sbom(self, image):
        # convert image name to a valid SBOM name
        image_name = image.replace("/", "_").replace(":", "_")

        # Add the image to the list of running containers
        self.semaphore_running_containers.acquire()
        try:
            self.list_of_running_containers.append(image_name + "_sbom")
        finally:
            self.semaphore_running_containers.release()

        command = [
            "docker",
            "run",
            "--rm",
            "-v",
            "/var/run/docker.sock:/var/run/docker.sock",
            "-v",
            f"{BuildUtils.build_dir}:/kaapana/trivy_results",
            "--name",
            image_name + "_sbom",
            self.trivy_image,
            "image",
            "--format",
            "cyclonedx",
            "--quiet",
            "--timeout",
            str(self.timeout) + "s",
            "--output",
            f"/kaapana/trivy_results/{image_name}_sbom.json",
            image,
        ]
        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=self.timeout,
        )

        if self.kill_flag:
            exit(1)
        elif output.returncode != 0:
            BuildUtils.logger.error(
                "Failed to create SBOM for image: "
                + image
                + "."
                + "Inspect the issue using the trivy --debug flag."
            )
            BuildUtils.logger.error(output.stderr)
            exit(1)

        # read the SBOM file
        with open(
            os.path.join(BuildUtils.build_dir, image_name + "_sbom.json"), "r"
        ) as f:
            sbom = json.load(f)

        # Remove the image from the list of running containers
        self.semaphore_running_containers.acquire()
        try:
            self.list_of_running_containers.remove(image_name + "_sbom")
        finally:
            self.semaphore_running_containers.release()

        self.semaphore_sboms.acquire()
        try:
            # add the SBOM to the dictionary
            self.sboms[image] = sbom
        finally:
            self.semaphore_sboms.release()

        # Remove the SBOM file
        os.remove(os.path.join(BuildUtils.build_dir, image_name + "_sbom.json"))

        return image

    # Function to check for vulnerabilities in a given image
    def create_vulnerability_report(self, image):
        # convert image name to a valid SBOM name
        image_name = image.replace("/", "_").replace(":", "_")

        self.semaphore_running_containers.acquire()
        try:
            self.list_of_running_containers.append(image_name + "_vulnerability_report")
        finally:
            self.semaphore_running_containers.release()

        command = [
            "docker",
            "run",
            "--rm",
            "-v",
            "/var/run/docker.sock:/var/run/docker.sock",
            "-v",
            f"{BuildUtils.build_dir}:/kaapana/trivy_results",
            "--name",
            image_name + "_vulnerability_report",
            self.trivy_image,
            "image",
            "--severity",
            BuildUtils.vulnerability_severity_level,
            "--format",
            "json",
            "--ignore-unfixed",
            "--quiet",
            "--timeout",
            str(self.timeout) + "s",
            "--output",
            f"/kaapana/trivy_results/{image_name}_vulnerability_report.json",
            image,
        ]

        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=self.timeout,
        )

        if self.kill_flag:
            exit(1)

        elif output.returncode != 0:
            BuildUtils.logger.error(
                "Failed to create vulnerability report for image: "
                + image
                + "."
                + "Inspect the issue using the trivy --debug flag."
            )
            BuildUtils.logger.error(output.stderr)
            exit(1)

        # read the vulnerability file
        with open(
            os.path.join(
                BuildUtils.build_dir, image_name + "_vulnerability_report.json"
            ),
            "r",
        ) as f:
            vulnerability_report = json.load(f)

        self.semaphore_running_containers.acquire()
        try:
            # Remove the container from the list of running containers
            self.list_of_running_containers.remove(image_name + "_vulnerability_report")
        finally:
            self.semaphore_running_containers.release()

        compressed_vulnerability_report = {}

        # Exit if vulnerabilities are found and exit on error is set
        if BuildUtils.exit_on_error == True and "Results" in vulnerability_report:
            # Check if there are any vulnerabilities
            if len(vulnerability_report["Results"]) > 0:
                BuildUtils.logger.error("Found vulnerabilities in image: " + image)
                for target in vulnerability_report["Results"]:
                    if "Vulnerabilities" in target:
                        BuildUtils.logger.error("")
                        BuildUtils.logger.error(
                            "-------- Target: " + target["Target"] + " --------"
                        )
                        BuildUtils.logger.error("")
                        for vulnerability in target["Vulnerabilities"]:
                            BuildUtils.logger.error(
                                "Vulnerability ID: " + vulnerability["VulnerabilityID"]
                            )
                            BuildUtils.logger.error("Pkg: " + vulnerability["PkgName"])
                            BuildUtils.logger.error(
                                "Installed Version: "
                                + vulnerability["InstalledVersion"]
                            )
                            BuildUtils.logger.error(
                                "Fixed Version: " + vulnerability["FixedVersion"]
                            )
                            BuildUtils.logger.error(
                                "Severity: " + vulnerability["Severity"]
                            )
                            # Not all vulnerabilities have a description
                            if "Description" in vulnerability:
                                BuildUtils.logger.error(
                                    "Description: " + vulnerability["Description"]
                                )
                            BuildUtils.logger.error("")
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name="Scan image: " + image,
                    msg="Found vulnerabilities in image: " + image,
                    level="ERROR",
                )
        # Create compressed vulnerability report
        elif "Results" in vulnerability_report:
            if len(vulnerability_report["Results"]) > 0:
                for target in vulnerability_report["Results"]:
                    if "Vulnerabilities" in target:
                        compressed_vulnerability_report[target["Target"]] = {}
                        for vulnerability in target["Vulnerabilities"]:
                            compressed_vulnerability_report[target["Target"]][
                                "VulnerabilityID"
                            ] = vulnerability["VulnerabilityID"]
                            compressed_vulnerability_report[target["Target"]][
                                "Pkg"
                            ] = vulnerability["PkgName"]
                            compressed_vulnerability_report[target["Target"]][
                                "InstalledVersion"
                            ] = vulnerability["InstalledVersion"]
                            compressed_vulnerability_report[target["Target"]][
                                "FixedVersion"
                            ] = vulnerability["FixedVersion"]
                            compressed_vulnerability_report[target["Target"]][
                                "Severity"
                            ] = vulnerability["Severity"]
                            # Not all vulnerabilities have a description
                            if "Description" in vulnerability:
                                compressed_vulnerability_report[target["Target"]][
                                    "Description"
                                ] = vulnerability["Description"]

        self.semaphore_vulnerability_reports.acquire()
        try:
            # Don't create vulnerability report if no vulnerabilities are found
            if not compressed_vulnerability_report == {}:
                # add the vulnerability report to the dictionary
                self.vulnerability_reports[image] = vulnerability_report

                # add the compressed vulnerability report to the dictionary
                self.compressed_vulnerability_reports[
                    image
                ] = compressed_vulnerability_report
        finally:
            self.semaphore_vulnerability_reports.release()
        # Remove the vulnerability report file
        os.remove(
            os.path.join(
                BuildUtils.build_dir, image_name + "_vulnerability_report.json"
            )
        )

        return image

    # Function to check the Kaapana chart for configuration errors
    def check_chart(self, path_to_chart):
        command = [
            "trivy",
            "config",
            "-f",
            "json",
            "-o",
            os.path.join(BuildUtils.build_dir, "chart_report.json"),
            "--severity",
            BuildUtils.configuration_check_severity_level,
            path_to_chart,
        ]
        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=self.timeout,
        )

        if output.returncode != 0:
            BuildUtils.logger.error("Failed to check Kaapana chart")
            BuildUtils.logger.error(output.stderr)
            BuildUtils.generate_issue(
                component=suite_tag,
                name="Check Kaapana chart",
                msg="Failed to check Kaapana chart" + path_to_chart,
                level="ERROR",
            )

        # read the chart report file
        with open(os.path.join(BuildUtils.build_dir, "chart_report.json"), "r") as f:
            chart_report = json.load(f)

        compressed_chart_report = {}

        # Log the chart report
        for report in chart_report["Results"]:
            if report["MisconfSummary"]["Failures"] > 0:
                compressed_chart_report[report["Target"]] = {}
                for misconfiguration in report["Misconfigurations"]:
                    if not misconfiguration["CauseMetadata"]["Code"]["Lines"] == None:
                        compressed_chart_report[report["Target"]]["Lines"] = (
                            str(misconfiguration["CauseMetadata"]["StartLine"])
                            + "-"
                            + str(misconfiguration["CauseMetadata"]["EndLine"])
                        )
                    compressed_chart_report[report["Target"]][
                        "Type"
                    ] = misconfiguration["Type"]
                    compressed_chart_report[report["Target"]][
                        "Title"
                    ] = misconfiguration["Title"]
                    compressed_chart_report[report["Target"]][
                        "Description"
                    ] = misconfiguration["Description"]
                    compressed_chart_report[report["Target"]][
                        "Message"
                    ] = misconfiguration["Message"]
                    compressed_chart_report[report["Target"]][
                        "Severity"
                    ] = misconfiguration["Severity"]

        # Safe the chart report to the build directory if there are any errors
        if not compressed_chart_report == {}:
            BuildUtils.logger.error(
                "Found configuration errors in Kaapana chart! See compressed_chart_report.json or chart_report.json for details."
            )
            with open(
                os.path.join(BuildUtils.build_dir, "compressed_chart_report.json"), "w"
            ) as f:
                json.dump(compressed_chart_report, f)

    # Function to check Dockerfile for configuration errors
    def check_dockerfile(self, path_to_dockerfile):

        command = [
            "trivy",
            "config",
            "-f",
            "json",
            "-o",
            os.path.join(BuildUtils.build_dir, "dockerfile_report.json"),
            "--severity",
            BuildUtils.configuration_check_severity_level,
            path_to_dockerfile,
        ]
        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=self.timeout,
        )

        if output.returncode != 0:
            BuildUtils.logger.error("Failed to check Dockerfile")
            BuildUtils.logger.error(output.stderr)
            BuildUtils.generate_issue(
                component=suite_tag,
                name="Check Dockerfile",
                msg="Failed to check Dockerfile: " + path_to_dockerfile,
                level="ERROR",
            )

        # Log the dockerfile report
        with open(
            os.path.join(BuildUtils.build_dir, "dockerfile_report.json"), "r"
        ) as f:
            dockerfile_report = json.load(f)

        # Check if the report contains any results -> weird if it doesn't e.g. when the Dockerfile is empty
        if not "Results" in dockerfile_report:
            BuildUtils.logger.warning(
                "No results found in dockerfile report. This is weird. Check the Dockerfile: "
                + path_to_dockerfile
            )
            return

        # Log the chart report
        for report in dockerfile_report["Results"]:
            if report["MisconfSummary"]["Failures"] > 0:
                if BuildUtils.exit_on_error:
                    BuildUtils.logger.error(
                        "Found configuration errors in Dockerfile! See dockerfile_report.json for details."
                    )
                    BuildUtils.generate_issue(
                        component=suite_tag,
                        name="Check Dockerfile",
                        msg="Found configuration errors in Dockerfile! See dockerfile_report.json for details.",
                        level="ERROR",
                    )
                self.compressed_dockerfile_report[path_to_dockerfile] = {}
                self.compressed_dockerfile_report[path_to_dockerfile][
                    report["Target"]
                ] = {}
                for misconfiguration in report["Misconfigurations"]:
                    if not misconfiguration["CauseMetadata"]["Code"]["Lines"] == None:
                        self.compressed_dockerfile_report[path_to_dockerfile][
                            report["Target"]
                        ]["Lines"] = (
                            str(misconfiguration["CauseMetadata"]["StartLine"])
                            + "-"
                            + str(misconfiguration["CauseMetadata"]["EndLine"])
                        )
                    self.compressed_dockerfile_report[path_to_dockerfile][
                        report["Target"]
                    ]["Title"] = misconfiguration["Title"]
                    self.compressed_dockerfile_report[path_to_dockerfile][
                        report["Target"]
                    ]["Description"] = misconfiguration["Description"]
                    self.compressed_dockerfile_report[path_to_dockerfile][
                        report["Target"]
                    ]["Message"] = misconfiguration["Message"]
                    self.compressed_dockerfile_report[path_to_dockerfile][
                        report["Target"]
                    ]["Severity"] = misconfiguration["Severity"]

        # Delete the dockerfile report file
        os.remove(os.path.join(BuildUtils.build_dir, "dockerfile_report.json"))

    def __error_clean_up(self):
        if not self.kill_flag:
            self.semaphore_running_containers.acquire()
            try:
                for container in self.list_of_running_containers:

                    command = ["docker", "kill", container]
                    run(command, check=False, stdout=DEVNULL, stderr=DEVNULL)

                    # remove empty json files
                    if os.path.exists(
                        os.path.join(BuildUtils.build_dir, container + ".json")
                    ):
                        os.remove(
                            os.path.join(BuildUtils.build_dir, container + ".json")
                        )
            finally:
                self.semaphore_running_containers.release()

    def __safe_sboms(self):
        # save the SBOMs to the build directory
        with open(os.path.join(BuildUtils.build_dir, "sboms.json"), "w") as f:
            json.dump(self.sboms, f)

    def create_sboms(self, list_of_images):

        try:
            with self.threadpool as threadpool:
                with alive_bar(
                    len(list_of_images), dual_line=True, title="Create SBOMS"
                ) as bar:
                    results = threadpool.imap_unordered(
                        self.create_sbom, list_of_images
                    )

                    # Loop through all built containers and scan them
                    for image_build_tag in results:
                        # Set progress bar text
                        bar.text(image_build_tag)
                        # Print progress bar
                        bar()
        except:
            self.__error_clean_up()
        finally:
            self.__safe_sboms()

    def __safe_vulnerability_reports(self):
        # save the vulnerability reports to the build directory
        with open(
            os.path.join(BuildUtils.build_dir, "vulnerability_reports.json"), "w"
        ) as f:
            json.dump(self.vulnerability_reports, f)

        with open(
            os.path.join(BuildUtils.build_dir, "compressed_vulnerability_report.json"),
            "w",
        ) as f:
            json.dump(self.compressed_vulnerability_reports, f)

    def create_vulnerability_reports(self, list_of_images):
        try:
            with self.threadpool as threadpool:
                with alive_bar(
                    len(list_of_images), dual_line=True, title="Vulnerability Scans"
                ) as bar:
                    results = threadpool.imap_unordered(
                        self.create_vulnerability_report, list_of_images
                    )

                    # Loop through all built containers and scan them
                    for image_build_tag in results:
                        # Set progress bar text
                        bar.text(image_build_tag)
                        # Print progress bar
                        bar()
        except:
            self.__error_clean_up()
        finally:
            self.__safe_vulnerability_reports()


if __name__ == "__main__":
    print("Please use the 'start_build.py' script to launch the build-process.")
    exit(1)
