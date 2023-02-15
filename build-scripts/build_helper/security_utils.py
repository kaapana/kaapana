#!/usr/bin/env python3
import os
from subprocess import PIPE, run
from build_helper.build_utils import BuildUtils
import json

suite_tag = "security"

# Class containing security related helper functions
# Using Trivy to create SBOMS and check for vulnerabilities
class TrivyUtils:
    def __init__(self):
        # Check if trivy is installed
        if not os.path.exists("/usr/local/bin/trivy"):
            BuildUtils.logger.error("Trivy is not installed, please visit https://aquasecurity.github.io/trivy/v0.37/getting-started/installation/ for installation instructions")

        self.sboms = {}
        self.vulnerability_reports = {}
        self.compressed_vulnerability_reports = {}

        # Check if severity level is set (enable all vulnerabily severity levels if not set)
        if BuildUtils.vulnerability_severity_level == '' or BuildUtils.vulnerability_severity_level == None:
            BuildUtils.vulnerability_severity_level = 'CRITICAL,HIGH,MEDIUM,LOW,UNKNOWN'
        # Check if vulnerability_severity_levels are in the allowed values
        elif not all(x in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN'] for x in BuildUtils.vulnerability_severity_level.split(",")):
            BuildUtils.logger.warning(f"Invalid severity level set in vulnerability_severity_level: {BuildUtils.vulnerability_severity_level}. Allowed values are: CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN")
            BuildUtils.generate_issue(
                "Invalid severity level set in vulnerability_severity_level",

            )
            
    # Function to create SBOM for a given image
    def create_sbom(self, image):
        command = ['trivy', 'image', '--format', 'cyclonedx', '--output', os.path.join(BuildUtils.build_dir, 'sbom.json') , image]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=3600)

        if output.returncode != 0:
            BuildUtils.logger.error("Failed to create SBOM for image: " + image)
            BuildUtils.logger.error(output.stderr)
            exit(1)

        # read the SBOM file
        with open(os.path.join(BuildUtils.build_dir, 'sbom.json'), 'r') as f:
            sbom = json.load(f)

        # add the SBOM to the dictionary
        self.sboms[image] = sbom

        # save the SBOMs to the build directory
        with open(os.path.join(BuildUtils.build_dir, 'sboms.json'), 'w') as f:
            json.dump(self.sboms, f)

        # Remove the SBOM file
        os.remove(os.path.join(BuildUtils.build_dir, 'sbom.json'))

    # Function to check for vulnerabilities in a given image
    def create_vulnerability_report(self, image):
        command = ['trivy', 'image', '-f', 'json', '-o', os.path.join(BuildUtils.build_dir, 'vulnerability_report.json'), '--ignore-unfixed', '--severity', BuildUtils.vulnerability_severity_level, image]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=3600)

        if output.returncode != 0:
            BuildUtils.logger.error("Failed to scan image: " + image)
            BuildUtils.logger.error(output.stderr)
            exit(1)

        # read the vulnerability file
        with open(os.path.join(BuildUtils.build_dir, 'vulnerability_report.json'), 'r') as f:
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
                exit(1)
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
                               
        # Don't create vulnerability report if no vulnerabilities are found
        if not compressed_vulnerability_report == {}:
            # add the vulnerability report to the dictionary
            self.vulnerability_reports[image] = vulnerability_report

            # add the compressed vulnerability report to the dictionary
            self.compressed_vulnerability_reports[image] = compressed_vulnerability_report

            # save the vulnerability reports to the build directory
            with open(os.path.join(BuildUtils.build_dir, 'vulnerability_reports.json'), 'w') as f:
                json.dump(self.vulnerability_reports, f)

            with open(os.path.join(BuildUtils.build_dir, 'compressed_vulnerability_reports.json'), 'w') as f:
                json.dump(self.compressed_vulnerability_reports, f)

        # Remove the vulnerability report file
        os.remove(os.path.join(BuildUtils.build_dir, 'vulnerability_report.json'))

    # Function to check the Kaapana chart for configuration errors
    @staticmethod
    def check_chart(path_to_chart):
        command = ['trivy', 'config', '-f', 'json', '-o', os.path.join(BuildUtils.build_dir, 'chart_report.json'), '--severity', BuildUtils.chart_check_severity_level, path_to_chart]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=3600)

        if output.returncode != 0:
            BuildUtils.logger.error("Failed to check Kaapana chart")
            BuildUtils.logger.error(output.stderr)
            exit(1)

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
        
if __name__ == '__main__':
    print("Please use the 'start_build.py' script to launch the build-process.")
    exit(1)