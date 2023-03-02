#!/usr/bin/env python3
import os
from subprocess import PIPE, run
from build_helper.build_utils import BuildUtils
import json
from shutil import which
import threading
import time
import requests

suite_tag = "security"
timeout = 3600

# Class containing security related helper functions
# Using Trivy to create SBOMS and check for vulnerabilities
class TrivyUtils:

    sboms = {}
    vulnerability_reports = {}
    compressed_vulnerability_reports = {}
    compressed_dockerfile_report = {}
    trivy_server_url = 'http://localhost:8081'
    trivy_server_id = ''
    server_connect_max_retries = 10
    
    def __init__(self):
        # Check if trivy is installed
        if which('trivy') is None:
            BuildUtils.logger.error("Trivy is not installed, please visit https://aquasecurity.github.io/trivy/v0.37/getting-started/installation/ for installation instructions")
            BuildUtils.generate_issue(
                component=suite_tag,
                name="Check if Trivy is installed",
                msg="Trivy is not installed",
                level="ERROR"
            )
        # Check if severity level is set (enable all vulnerabily severity levels if not set)
        if BuildUtils.vulnerability_severity_level == '' or BuildUtils.vulnerability_severity_level == None:
            BuildUtils.vulnerability_severity_level = 'CRITICAL,HIGH,MEDIUM,LOW,UNKNOWN'
        # Check if vulnerability_severity_levels are in the allowed values
        elif not all(x in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN'] for x in BuildUtils.vulnerability_severity_level.split(",")):
            BuildUtils.logger.warning(f"Invalid severity level set in vulnerability_severity_level: {BuildUtils.vulnerability_severity_level}. Allowed values are: CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN")
            BuildUtils.generate_issue(
                component=suite_tag,
                name="Check if vulnerability_severity_level is set correctly",
                msg="Invalid severity level set in vulnerability_severity_level",
                level="ERROR"
            )

        self.semaphore_sboms = threading.Lock()
        self.semaphore_vulnerability_reports = threading.Lock()
        self.semaphore_compressed_dockerfile_report = threading.Lock()

    def start_trivy_server(self):
        command = ['docker', 'run', '-p', '8081:80', '--detach', 'aquasec/trivy:latest', 'server', '--listen', '0.0.0.0:80']
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=timeout)

        self.trivy_server_id = output.stdout.strip()

        retry_count = 0

        # Keep trying to connect until the server responds with 200 OK, or we've retried too many times
        while retry_count < self.server_connect_max_retries:
            try:
                output = run(['trivy', 'image', '--server', self.trivy_server_url, 'aquasec/trivy:latest'], stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=timeout)
                if output.returncode == 0:
                    # Server is ready,
                    break
            except requests.exceptions.RequestException:
                pass
            retry_count += 1
            time.sleep(3)
            BuildUtils.logger.error("Server is not ready yet, retrying...")

        # If we've retried too many times, print an error message
        if retry_count == self.server_connect_max_retries:
            BuildUtils.logger.error("Error: Server did not respond after {} retries".format(self.server_connect_max_retries))

    def stop_trivy_server(self):
        command = ['docker', 'stop', self.trivy_server_id]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=timeout)

        if output.returncode != 0:
            BuildUtils.logger.error("Failed to stop Trivy server")
            BuildUtils.logger.error(output.stderr)
            BuildUtils.generate_issue(
                component=suite_tag,
                name="Stop Trivy server",
                msg="Failed to stop Trivy server",
                level="ERROR"
            )
                   
    # Function to create SBOM for a given image
    def create_sbom(self, image):
        # convert image name to a valid SBOM name
        image_name = image.replace('/', '_').replace(':', '_')

        command = ['trivy', 'image', '--server', self.trivy_server_url, '--timeout', str(timeout) + 's', '--format', 'cyclonedx', '--output', os.path.join(BuildUtils.build_dir, image_name + '_sbom.json') , image]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=timeout)

        if output.returncode != 0:
            BuildUtils.logger.error("Failed to create SBOM for image: " + image)
            BuildUtils.logger.error(output.stderr)
            BuildUtils.generate_issue(
                component=suite_tag,
                name="Create SBOM for image: " + image,
                msg="Failed to create SBOM for image: " + image,
                level="ERROR"
            )

        # read the SBOM file
        with open(os.path.join(BuildUtils.build_dir, image_name + '_sbom.json'), 'r') as f:
            sbom = json.load(f)

        self.semaphore_sboms.acquire()
        try:
            # add the SBOM to the dictionary
            self.sboms[image] = sbom
        finally:
            self.semaphore_sboms.release()

        # Remove the SBOM file
        os.remove(os.path.join(BuildUtils.build_dir, image_name + '_sbom.json'))

        return image

    # Function to check for vulnerabilities in a given image
    def create_vulnerability_report(self, image):
        # convert image name to a valid SBOM name
        image_name = image.replace('/', '_').replace(':', '_')

        command = ['trivy', 'image', '--server', self.trivy_server_url, '--timeout', str(timeout) + 's', '-f', 'json', '-o', os.path.join(BuildUtils.build_dir, image_name + '_vulnerability_report.json'), '--ignore-unfixed', '--severity', BuildUtils.vulnerability_severity_level, image]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=timeout)

        if output.returncode != 0:
            BuildUtils.logger.error("Failed to scan image: " + image)
            BuildUtils.logger.error(output.stderr)
            BuildUtils.generate_issue(
                component=suite_tag,
                name="Scan image: " + image,
                msg="Failed to scan image: " + image,
                level="ERROR"
            )
        # convert image name to a valid SBOM name
        image_name = image.replace('/', '_').replace(':', '_')

        # read the vulnerability file
        with open(os.path.join(BuildUtils.build_dir, image_name + '_vulnerability_report.json'), 'r') as f:
            vulnerability_report = json.load(f)

        compressed_vulnerability_report = {}

        # Exit if vulnerabilities are found and exit on error is set
        if BuildUtils.exit_on_error == True and 'Results' in vulnerability_report:
            # Check if there are any vulnerabilities
            if len(vulnerability_report['Results']) > 0:
                BuildUtils.logger.error("Found vulnerabilities in image: " + image)
                for target in vulnerability_report['Results']:
                    if 'Vulnerabilities' in target:
                        BuildUtils.logger.error('')
                        BuildUtils.logger.error("-------- Target: " + target['Target'] + " --------")
                        BuildUtils.logger.error('')
                        for vulnerability in target['Vulnerabilities']:
                            BuildUtils.logger.error("Vulnerability ID: " + vulnerability['VulnerabilityID'])
                            BuildUtils.logger.error("Pkg: " + vulnerability['PkgName'])
                            BuildUtils.logger.error("Installed Version: " + vulnerability['InstalledVersion'])
                            BuildUtils.logger.error("Fixed Version: " + vulnerability['FixedVersion'])
                            BuildUtils.logger.error("Severity: " + vulnerability['Severity'])
                            # Not all vulnerabilities have a description
                            if 'Description' in vulnerability:
                                BuildUtils.logger.error("Description: " + vulnerability['Description'])
                            BuildUtils.logger.error("")    
                BuildUtils.generate_issue(
                component=suite_tag,
                name="Scan image: " + image,
                msg="Found vulnerabilities in image: " + image,
                level="ERROR"
                )
        # Create compressed vulnerability report
        elif 'Results' in vulnerability_report:
            if len(vulnerability_report['Results']) > 0:
                for target in vulnerability_report['Results']:
                    if 'Vulnerabilities' in target:
                        compressed_vulnerability_report[target['Target']] = {}
                        for vulnerability in target['Vulnerabilities']:
                            compressed_vulnerability_report[target['Target']]['VulnerabilityID'] = vulnerability['VulnerabilityID']
                            compressed_vulnerability_report[target['Target']]['Pkg'] = vulnerability['PkgName']
                            compressed_vulnerability_report[target['Target']]['InstalledVersion'] = vulnerability['InstalledVersion']
                            compressed_vulnerability_report[target['Target']]['FixedVersion'] = vulnerability['FixedVersion']
                            compressed_vulnerability_report[target['Target']]['Severity'] = vulnerability['Severity']
                            # Not all vulnerabilities have a description
                            if 'Description' in vulnerability:
                                compressed_vulnerability_report[target['Target']]['Description'] = vulnerability['Description']

        self.semaphore_vulnerability_reports.acquire()
        try:            
            # Don't create vulnerability report if no vulnerabilities are found
            if not compressed_vulnerability_report == {}:
                # add the vulnerability report to the dictionary
                self.vulnerability_reports[image] = vulnerability_report

                # add the compressed vulnerability report to the dictionary
                self.compressed_vulnerability_reports[image] = compressed_vulnerability_report
        finally:
            self.semaphore_vulnerability_reports.release()
        # Remove the vulnerability report file
        os.remove(os.path.join(BuildUtils.build_dir, image_name + '_vulnerability_report.json'))

        return image

    # Function to check the Kaapana chart for configuration errors
    @staticmethod
    def check_chart(path_to_chart):
        command = ['trivy', 'config', '-f', 'json', '-o', os.path.join(BuildUtils.build_dir, 'chart_report.json'), '--severity', BuildUtils.configuration_check_severity_level, path_to_chart]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=timeout)

        if output.returncode != 0:
            BuildUtils.logger.error("Failed to check Kaapana chart")
            BuildUtils.logger.error(output.stderr)
            BuildUtils.generate_issue(
                component=suite_tag,
                name="Check Kaapana chart",
                msg="Failed to check Kaapana chart" + path_to_chart,
                level="ERROR"
            )

        # read the chart report file
        with open(os.path.join(BuildUtils.build_dir, 'chart_report.json'), 'r') as f:
            chart_report = json.load(f)

        compressed_chart_report = {}

        # Log the chart report
        for report in chart_report['Results']:
            if report['MisconfSummary']['Failures'] > 0:  
                compressed_chart_report[report['Target']] = {}
                for misconfiguration in report['Misconfigurations']:
                    if not misconfiguration['CauseMetadata']['Code']['Lines'] == None:
                        compressed_chart_report[report['Target']]['Lines'] = str(misconfiguration['CauseMetadata']['StartLine']) + "-" + str(misconfiguration['CauseMetadata']['EndLine'])
                    compressed_chart_report[report['Target']]['Type'] = misconfiguration['Type']
                    compressed_chart_report[report['Target']]['Title'] = misconfiguration['Title']
                    compressed_chart_report[report['Target']]['Description'] = misconfiguration['Description']
                    compressed_chart_report[report['Target']]['Message'] = misconfiguration['Message']
                    compressed_chart_report[report['Target']]['Severity'] = misconfiguration['Severity']

        # Safe the chart report to the build directory if there are any errors
        if not compressed_chart_report == {}:
            BuildUtils.logger.error("Found configuration errors in Kaapana chart! See compressed_chart_report.json or chart_report.json for details.")
            with open(os.path.join(BuildUtils.build_dir, 'compressed_chart_report.json'), 'w') as f:
                json.dump(compressed_chart_report, f)

    # Function to check Dockerfile for configuration errors
    def check_dockerfile(self, path_to_dockerfile):

        command = ['trivy', 'config', '-f', 'json', '-o', os.path.join(BuildUtils.build_dir, 'dockerfile_report.json'), '--severity', BuildUtils.configuration_check_severity_level, path_to_dockerfile]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=timeout)

        if output.returncode != 0:
            BuildUtils.logger.error("Failed to check Dockerfile")
            BuildUtils.logger.error(output.stderr)
            BuildUtils.generate_issue(
                component=suite_tag,
                name="Check Dockerfile",
                msg="Failed to check Dockerfile: " + path_to_dockerfile,
                level="ERROR"
            )

        # Log the dockerfile report
        with open(os.path.join(BuildUtils.build_dir, 'dockerfile_report.json'), 'r') as f:
            dockerfile_report = json.load(f)
        
        # Check if the report contains any results -> weird if it doesn't e.g. when the Dockerfile is empty
        if not 'Results' in dockerfile_report:
            BuildUtils.logger.warning("No results found in dockerfile report. This is weird. Check the Dockerfile: " + path_to_dockerfile)
            return

        # Log the chart report
        for report in dockerfile_report['Results']:
            if report['MisconfSummary']['Failures'] > 0: 
                if BuildUtils.exit_on_error:
                    BuildUtils.logger.error("Found configuration errors in Dockerfile! See dockerfile_report.json for details.")
                    BuildUtils.generate_issue(
                    component=suite_tag,
                    name="Check Dockerfile",
                    msg="Found configuration errors in Dockerfile! See dockerfile_report.json for details.",
                    level="ERROR"
                    )
                self.compressed_dockerfile_report[path_to_dockerfile] = {}
                self.compressed_dockerfile_report[path_to_dockerfile][report['Target']] = {}
                for misconfiguration in report['Misconfigurations']:
                    if not misconfiguration['CauseMetadata']['Code']['Lines'] == None:
                        self.compressed_dockerfile_report[path_to_dockerfile][report['Target']]['Lines'] = str(misconfiguration['CauseMetadata']['StartLine']) + "-" + str(misconfiguration['CauseMetadata']['EndLine'])
                    self.compressed_dockerfile_report[path_to_dockerfile][report['Target']]['Title'] = misconfiguration['Title']
                    self.compressed_dockerfile_report[path_to_dockerfile][report['Target']]['Description'] = misconfiguration['Description']
                    self.compressed_dockerfile_report[path_to_dockerfile][report['Target']]['Message'] = misconfiguration['Message']
                    self.compressed_dockerfile_report[path_to_dockerfile][report['Target']]['Severity'] = misconfiguration['Severity']

        # Delete the dockerfile report file
        os.remove(os.path.join(BuildUtils.build_dir, 'dockerfile_report.json'))

if __name__ == '__main__':
    print("Please use the 'start_build.py' script to launch the build-process.")
    exit(1)