#!/usr/bin/env python3
import os
from subprocess import PIPE, run, DEVNULL
from build_helper.build_utils import BuildUtils
import json
from shutil import which
import threading
from multiprocessing.pool import ThreadPool
from alive_progress import alive_bar
import datetime

suite_tag = "security"

# Class containing security related helper functions
# Using Trivy to create SBOMS and check for vulnerabilities
class TrivyUtils:
    trivy_image = "aquasec/trivy:0.38.3"
    timeout = 10000
    threadpool = None
    list_of_running_containers = []
    kill_flag = False
    cache = True
    tag = None
    dockerfile_report_path = None

    def __init__(self, cache=True, tag=None):
        if tag is None:
            raise Exception("Please provide a tag")

        self.tag
        self.cache = cache

        if BuildUtils.configuration_check:
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

        run(["docker", "logout", "ghcr.io"], stdout=DEVNULL, stderr=DEVNULL)

        self.semaphore_sboms = threading.Lock()
        self.semaphore_vulnerability_reports = threading.Lock()
        self.semaphore_compressed_dockerfile_report = threading.Lock()
        self.semaphore_running_containers = threading.Lock()
        self.semaphore_threadpool = threading.Lock()

        self.threadpool = ThreadPool(BuildUtils.parallel_processes)

        # create reports path (/kaapana/security-reports)
        self.reports_path = os.path.normpath(
            os.path.join(BuildUtils.build_dir, "..", "security-reports")
        )

        os.makedirs(self.reports_path, exist_ok=True)

        self.database_timestamp = self.get_database_next_update_timestamp()

    def create_vulnerability_reports(self, list_of_images):

        # create raw reports path (/kaapana/security-reports/raw)
        self.raw_reports_path = os.path.join(self.reports_path, self.tag, "raw")
        os.makedirs(self.raw_reports_path, exist_ok=True)

        # create compressed reports path (/kaapana/security-reports/compressed)
        self.compressed_reports_path = os.path.join(
            self.reports_path, self.tag, "compressed"
        )
        os.makedirs(self.compressed_reports_path, exist_ok=True)

        # if self.cache:
        #     self.load_cache()
        try:
            with self.threadpool as threadpool:
                with alive_bar(
                    len(list_of_images), dual_line=True, title="Vulnerability Scans"
                ) as bar:
                    with self.semaphore_threadpool:
                        results = threadpool.imap_unordered(
                            self.create_vulnerability_report, list_of_images
                        )

                    # Loop through all built containers and scan them
                    for image_build_tag, error in results:
                        if error is not None:
                            raise Exception(error["description"])
                        # Set progress bar text
                        bar.text(image_build_tag)
                        # Print progress bar
                        bar()
        except Exception as e:
            BuildUtils.logger.error(f"{e}")
            with self.semaphore_threadpool:
                if self.threadpool is not None:
                    self.threadpool.terminate()
                    self.threadpool = None
            self.error_clean_up()
        finally:
            self.compress_vulnerability_reports()

    # Function to check for vulnerabilities in a given image
    def create_vulnerability_report(self, image):
        issue = None

        if self.cache:
            if self.check_vulnerability_reports_cache(image):
                return image, issue

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
            f"{self.raw_reports_path}:/kaapana/trivy_results",
            "--name",
            image_name + "_vulnerability_report",
            self.trivy_image,
            "image",
            "--severity",
            BuildUtils.vulnerability_severity_level,
            "--format",
            "json",
            "--ignore-unfixed",
            "--skip-dirs",
            "usr/local/lib/python3.8/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "usr/local/lib/python3.8/site-packages/nibabel/tests/data",
            "--skip-dirs",
            "usr/local/lib/python3.9/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "usr/local/lib/python3.9/site-packages/nibabel/tests/data",
            "--skip-dirs",
            "usr/local/lib/python3.10/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "usr/local/lib/python3.10/site-packages/nibabel/tests/data",
            "--skip-dirs",
            "usr/local/lib/python3.11/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "usr/local/lib/python3.11/site-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.8/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.8/site-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.9/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.9/site-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.10/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.10/site-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.11/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.11/site-packages/nibabel/tests/data",
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
            issue = {
                "component": image,
                "level": "FATAL",
                "description": "Vulnerability scan was interrupted.",
            }
            return image, issue
        elif output.returncode != 0:
            BuildUtils.logger.error(
                "Failed to create vulnerability report for image: "
                + image
                + "."
                + "Inspect the issue using the trivy --debug flag."
            )
            BuildUtils.logger.error(output.stderr)
            issue = {
                "component": image,
                "level": "FATAL",
                "description": "Failed to create vulnerability report.",
            }
            return image, issue

        # read the vulnerability file
        with open(
            os.path.join(
                self.raw_reports_path, image_name + "_vulnerability_report.json"
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
                BuildUtils.logger.error("Vulnerabilities found in image: " + image)
                issue = {
                    "component": image,
                    "level": "ERROR",
                    "description": "Vulnerabilities found in image.",
                }
                return image, issue
        # Create compressed vulnerability report

        self.semaphore_vulnerability_reports.acquire()
        try:
            vulnerability_report["Metadata"]["NextUpdate"] = self.database_timestamp
            # self.vulnerability_reports[image] = vulnerability_report
        finally:
            self.semaphore_vulnerability_reports.release()

        if self.kill_flag:
            issue = {
                "component": image,
                "level": "FATAL",
                "description": "SBOM creation was interrupted",
            }
            return image, issue

        elif output.returncode != 0:
            BuildUtils.logger.error(
                "Failed to create SBOM for image: "
                + image
                + "."
                + "Inspect the issue using the trivy --debug flag."
            )
            BuildUtils.logger.error(output.stderr)
            issue = {
                "component": image,
                "level": "FATAL",
                "description": "Failed to create SBOM for image: "
                + image
                + "."
                + "Inspect the issue using the trivy --debug flag.",
            }
            return image, issue

        return image, issue

    def create_sboms(self, list_of_images):

        # create sboms path (/kaapana/security-reports/sboms)
        self.sboms_path = os.path.join(self.reports_path, self.tag, "sboms")
        os.makedirs(self.sboms_path, exist_ok=True)

        try:
            with self.threadpool as threadpool:
                with alive_bar(
                    len(list_of_images), dual_line=True, title="Create SBOMS"
                ) as bar:
                    with self.semaphore_threadpool:
                        results = threadpool.imap_unordered(
                            self.create_sbom, list_of_images
                        )

                    # Loop through all built containers and scan them
                    for image_build_tag, error in results:
                        if error is not None:
                            raise Exception(error["description"])
                        # Set progress bar text
                        bar.text(image_build_tag)
                        # Print progress bar
                        bar()
        except Exception as e:
            BuildUtils.logger.error(f"{e}")
            with self.semaphore_threadpool:
                if self.threadpool is not None:
                    self.threadpool.terminate()
                    self.threadpool = None
            self.error_clean_up()
        finally:
            pass
            # self.safe_sboms()

    # Function to create SBOM for a given image
    def create_sbom(self, image):
        issue = None
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
            f"{self.sboms_path}:/kaapana/trivy_results",
            "--name",
            image_name + "_sbom",
            self.trivy_image,
            "image",
            "--format",
            "cyclonedx",
            "--skip-dirs",
            "usr/local/lib/python3.8/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "usr/local/lib/python3.8/site-packages/nibabel/tests/data",
            "--skip-dirs",
            "usr/local/lib/python3.9/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "usr/local/lib/python3.9/site-packages/nibabel/tests/data",
            "--skip-dirs",
            "usr/local/lib/python3.10/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "usr/local/lib/python3.10/site-packages/nibabel/tests/data",
            "--skip-dirs",
            "usr/local/lib/python3.11/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "usr/local/lib/python3.11/site-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.8/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.8/site-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.9/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.9/site-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.10/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.10/site-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.11/dist-packages/nibabel/tests/data",
            "--skip-dirs",
            "opt/conda/lib/python3.11/site-packages/nibabel/tests/data",
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
            issue = {
                "component": image,
                "level": "FATAL",
                "description": "SBOM creation was interrupted",
            }
            return image, issue

        elif output.returncode != 0:
            BuildUtils.logger.error(
                "Failed to create SBOM for image: "
                + image
                + "."
                + "Inspect the issue using the trivy --debug flag."
            )
            BuildUtils.logger.error(output.stderr)
            issue = {
                "component": image,
                "level": "FATAL",
                "description": "Failed to create SBOM for image: "
                + image
                + "."
                + "Inspect the issue using the trivy --debug flag.",
            }
            return image, issue

        # Remove the image from the list of running containers
        self.semaphore_running_containers.acquire()
        try:
            self.list_of_running_containers.remove(image_name + "_sbom")
        finally:
            self.semaphore_running_containers.release()

        return image, issue

    # Function to check the Kaapana chart for configuration errors
    def check_chart(self, path_to_chart):
        command = [
            "trivy",
            "config",
            "-f",
            "json",
            "-o",
            os.path.join(
                self.reports_path, self.tag,
                "chart_report.json",
            ),
            "--severity",
            BuildUtils.configuration_check_severity_level,
            path_to_chart,
        ]
        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=self.timeout * 2,
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
        with open(
            os.path.join(
                self.reports_path, self.tag,
                "chart_report.json",
            ),
            "r",
        ) as f:
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

        # Safe the chart report to the security-reports directory if there are any errors
        if not compressed_chart_report == {}:
            BuildUtils.logger.error(
                "Found configuration errors in Kaapana chart! See compressed_chart_report.json or chart_report.json for details."
            )
            with open(
                os.path.join(
                    self.reports_path, self.tag,
                    "compressed_chart_report.json",
                ),
                "w",
            ) as f:
                json.dump(compressed_chart_report, f)

        # move docker file report to security-reports directory
        if os.path.exists(
            os.path.join(
                self.reports_path,
                "dockerfile_reports",
                )
            ):
            os.rename(
                os.path.join(
                    self.reports_path,
                    "dockerfile_reports",
                    ),
                os.path.join(
                    self.reports_path,
                    self.tag,
                    "dockerfile_reports",
                    ),
            )

    # Function to check Dockerfile for configuration errors
    def check_dockerfile(self, path_to_dockerfile):

        module = "_".join(path_to_dockerfile.split("/")[-4:-1])

        command = [
            "trivy",
            "config",
            "-f",
            "json",
            "-o",
            os.path.join(self.dockerfile_report_path, f"{module}.json"),
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
            os.path.join(self.dockerfile_report_path, f"{module}.json"), "r"
        ) as f:
            dockerfile_report = json.load(f)

        # Check if the report contains any results -> weird if it doesn't e.g. when the Dockerfile is empty
        if not "Results" in dockerfile_report:
            BuildUtils.logger.warning(
                "No results found in dockerfile report. This is weird. Check the Dockerfile: "
                + path_to_dockerfile
            )
            return

    def modules_to_cves(self):
        list_of_vulnerability_reports = os.listdir(self.raw_reports_path)
        module_vulnerability_count = {}
        for vulnerability_report in list_of_vulnerability_reports:
            # Load the vulnerability report
            with open(
                os.path.join(self.raw_reports_path, vulnerability_report), "r"
            ) as f:
                vulnerability_report = json.load(f)

                # Create compressed vulnerability report
                compressed_vulnerability_report = {}
                if "Results" in vulnerability_report:
                    if len(vulnerability_report["Results"]) > 0:
                        for target in vulnerability_report["Results"]:
                            if "Vulnerabilities" in target:
                                for vulnerability in target["Vulnerabilities"]:
                                    compressed_vulnerability_report[
                                        vulnerability["VulnerabilityID"]
                                    ] = {}

                                    compressed_vulnerability_report[
                                        vulnerability["VulnerabilityID"]
                                    ]["Class"] = target["Class"]
                                    compressed_vulnerability_report[
                                        vulnerability["VulnerabilityID"]
                                    ]["Type"] = target["Type"]

                                    compressed_vulnerability_report[
                                        vulnerability["VulnerabilityID"]
                                    ]["Pkg"] = vulnerability["PkgName"]
                                    compressed_vulnerability_report[
                                        vulnerability["VulnerabilityID"]
                                    ]["InstalledVersion"] = vulnerability[
                                        "InstalledVersion"
                                    ]

                                    if "FixedVersion" in vulnerability:
                                        compressed_vulnerability_report[
                                            vulnerability["VulnerabilityID"]
                                        ]["FixedVersion"] = vulnerability[
                                            "FixedVersion"
                                        ]
                                    else:
                                        compressed_vulnerability_report[
                                            vulnerability["VulnerabilityID"]
                                        ]["FixedVersion"] = None

                                    compressed_vulnerability_report[
                                        vulnerability["VulnerabilityID"]
                                    ]["Severity"] = vulnerability["Severity"]
                                    # Not all vulnerabilities have a description
                                    if "Description" in vulnerability:
                                        compressed_vulnerability_report[
                                            vulnerability["VulnerabilityID"]
                                        ]["Description"] = vulnerability["Description"]
                                    else:
                                        compressed_vulnerability_report[
                                            vulnerability["VulnerabilityID"]
                                        ]["Description"] = None
                with open(
                    os.path.join(
                        self.compressed_reports_path,
                        vulnerability_report["ArtifactName"]
                        .replace("/", "_")
                        .replace(":", "_")
                        + "_vulnerability_report.json",
                    ),
                    "w",
                ) as f:
                    json.dump(compressed_vulnerability_report, f)
            
            module_vulnerability_count[vulnerability_report["ArtifactName"]] = len(compressed_vulnerability_report)

        with open(
            os.path.join(
                self.reports_path,
                self.tag,
                "module_vulnerability_count.json",
            ),
            "w",
        ) as f:
            json.dump(module_vulnerability_count, f)

    def compress_vulnerability_reports(self):
        # Create compressed vulnerability reports
        self.modules_to_cves()
        #
        self.extract_individual_cves()

    def error_clean_up(self):
        self.kill_flag = True
        self.semaphore_running_containers.acquire()
        try:
            for container in self.list_of_running_containers:
                command = ["docker", "kill", container]
                run(command, check=False, stdout=DEVNULL, stderr=DEVNULL)

                # remove empty json files
                # if os.path.exists(os.path.join(self.reports_path, container + ".json")):
                #    os.remove(os.path.join(self.reports_path, container + ".json"))
                # TODO: remove empty json files in raw
        finally:
            self.semaphore_running_containers.release()

    # Read the NextUpdate timestamp from the database and check if it has expired
    def check_database_expired(self, image):
        timestamp = self.vulnerability_reports[image]["Metadata"]["NextUpdate"]
        timestamp_object = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")

        # Check if the timestamp has expired (UTC)
        if datetime.datetime.utcnow() > timestamp_object:
            return True
        else:
            return False

    def check_vulnerability_reports_cache(self, image):
        # Check if the image is in the vulnerability reports
        path_to_report = os.path.join(
            self.raw_reports_path,
            f"{image}_vulnerability_report.json".replace("/", "_").replace(":", "_"),
        )
        if os.path.isfile(path_to_report):
            try:
                report = json.load(open(path_to_report))
            except Exception as e:
                return False
            # Check if the image hash is the same
            if report["Metadata"]["ImageID"] == self.get_image_Id(image):
                # Check if the database has expired
                if (
                    BuildUtils.check_expired_vulnerabilities_database
                    and self.check_database_expired(image)
                ):
                    return False
                return True

        return False

    def get_image_Id(self, image):
        try:
            # Get the image digest
            command = f"docker inspect {image}"
            result = run(command, shell=True, stdout=PIPE, stderr=PIPE, text=True)

            # Check if the command was successful
            if result.returncode == 0:
                # Get the image digest
                return json.loads(result.stdout)[0]["Id"]
            else:
                raise Exception(result.stderr)

        except Exception as e:
            BuildUtils.logger.error(f"Failed to get the image digest: {e}")
            return None

    # docker run --rm aquasec/trivy:0.38.3 image --quiet --download-db-only && trivy --version
    def get_database_next_update_timestamp(self):
        command = " ".join(
            [
                "docker run --rm --entrypoint /bin/sh",
                self.trivy_image,
                '-c "trivy image --quiet --download-db-only; trivy --version"',
            ]
        )

        output = run(
            command, shell=True, check=False, stdout=PIPE, stderr=PIPE, text=True
        )

        if output.returncode != 0:
            BuildUtils.logger.error(
                "Failed to get the timestamp of the last database download."
            )
            raise Exception(output.stderr)

        # Get the timestamp of the last database download
        # Ignore the under second part of the timestamp
        return output.stdout.split("NextUpdate: ")[1].split(".")[0]
        # timestamp_object = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")

    def extract_individual_cves(self):
        cves = {}
        list_of_vulnerability_reports = os.listdir(self.raw_reports_path)

        for vulnerability_report in list_of_vulnerability_reports:
            # Load the vulnerability report
            with open(
                os.path.join(self.raw_reports_path, vulnerability_report), "r"
            ) as f:
                report = json.load(f)

            if "Results" in report:
                for issue in report["Results"]:
                    if "Vulnerabilities" in issue:
                        for vulnerability in issue["Vulnerabilities"]:
                            if (
                                vulnerability["Severity"]
                                in BuildUtils.vulnerability_severity_level
                            ):
                                if not vulnerability["VulnerabilityID"] in cves:
                                    cves[vulnerability["VulnerabilityID"]] = {
                                        "Class": issue["Class"]
                                        if "Class" in issue
                                        else None,
                                        "Type": issue["Type"]
                                        if "Type" in issue
                                        else None,
                                        "Title": vulnerability["Title"]
                                        if "Title" in vulnerability
                                        else None,
                                        "PkgName": vulnerability["PkgName"],
                                        "PublishedDate": vulnerability["PublishedDate"]
                                        if "PublishedDate" in vulnerability
                                        else None,
                                        "LastModifiedDate": vulnerability[
                                            "LastModifiedDate"
                                        ]
                                        if "LastModifiedDate" in vulnerability
                                        else None,
                                        "InstalledVersion": vulnerability[
                                            "InstalledVersion"
                                        ],
                                        "FixedVersion": vulnerability["FixedVersion"]
                                        if "FixedVersion" in vulnerability
                                        else None,
                                        "Severity": vulnerability["Severity"],
                                        "SeveritySource": vulnerability[
                                            "SeveritySource"
                                        ]
                                        if "SeveritySource" in vulnerability
                                        else None,
                                        "Target": issue["Type"]
                                        if issue["Type"] in issue["Target"]
                                        else issue["Target"],
                                        "Modules": [report["ArtifactName"]],
                                    }
                                else:
                                    if (
                                        not report["ArtifactName"]
                                        in cves[vulnerability["VulnerabilityID"]][
                                            "Modules"
                                        ]
                                    ):
                                        cves[vulnerability["VulnerabilityID"]][
                                            "Modules"
                                        ].append(report["ArtifactName"])

        BuildUtils.logger.info(f"Found {len(cves)} individual vulnerabilities")

        with open(
            os.path.join(self.reports_path, self.tag, self.tag + "_cves.json"), "w"
        ) as f:
            json.dump(cves, f, indent=4)


if __name__ == "__main__":
    print("Please use the 'start_build.py' script to launch the build-process.")
    exit(1)
