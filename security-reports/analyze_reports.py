#!/usr/bin/env python3
import argparse
import logging
import os
import json

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.INFO)

c_format = logging.Formatter("%(levelname)s - %(message)s")
c_handler.setFormatter(c_format)

logger.addHandler(c_handler)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--tag",
        dest="tag",
        default=None,
        required=False,
        help="Plattform version: e.g.: 0.1.3-591-g6426ef53",
    )
    parser.add_argument(
        "-p",
        "--python",
        action="store_true",
        dest="python",
        default=False,
        help="Analyze only python reports",
    )
    parser.add_argument(
        "-j",
        "--java",
        action="store_true",
        dest="java",
        default=False,
        help="Analyze only java reports",
    )
    parser.add_argument(
        "-os",
        "--os",
        action="store_true",
        dest="os",
        default=False,
        help="Analyze only os reports",
    )
    parser.add_argument(
        "-s",
        "--severity",
        dest="severity",
        default="CRITICAL,HIGH,MEDIUM,LOW,UNKNOWN",
        help="Comma separated list of severity levels to analyze",
    )
    parser.add_argument(
        "-iuf",
        "--ignore-unfixed",
        action="store_true",
        dest="ignore_unfixed",
        default=False,
        help="Ignore unfixed vulnerabilities",
    )

    
    args = parser.parse_args()

    tag = args.tag
    severity = args.severity.split(",")
    ignore_unfixed = args.ignore_unfixed

    java_reports = args.java
    python_reports = args.python
    os_reports = args.os

    if java_reports and python_reports:
        logger.error("Cannot analyze java and python reports at the same time")
        exit(1)
    
    if java_reports and os_reports:
        logger.error("Cannot analyze java and os reports at the same time")
        exit(1)

    if python_reports and os_reports:
        logger.error("Cannot analyze python and os reports at the same time")
        exit(1)

    logger.info(f"Analyzing reports for tag {tag} with severity {severity}")

    # load report
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), tag + "_vulnerability_reports.json")

    if not os.path.exists(report_path):
        logger.error(f"Report {report_path} does not exist")
        exit(1)

    with open(report_path, "r") as f:
        reports = json.load(f)

    cves = {}

    logger.info(f"Found {len(reports)} reports: ")
    for module in reports:
        if 'Results' in reports[module]:
            for issue in reports[module]['Results']:
                if 'Vulnerabilities' in issue:
                    for vulnerability in issue['Vulnerabilities']:
                        if vulnerability['Severity'] in severity:
                            if not vulnerability['VulnerabilityID'] in cves:

                                if java_reports and issue['Target'] != "Java":
                                    continue
                                if python_reports and issue['Target'] != "Python":
                                    continue
                                if os_reports and issue['Class'] != "os-pkgs":
                                    continue
                                if ignore_unfixed and not 'FixedVersion' in vulnerability:
                                    continue
                                
                                cves[vulnerability['VulnerabilityID']] = {
                                    "Class": issue['Class'] if 'Class' in issue else None,
                                    "Type": issue['Type'] if 'Type' in issue else None,
                                    "Title": vulnerability['Title'] if 'Title' in vulnerability else None,
                                    "PkgName": vulnerability['PkgName'],
                                    "PublishedDate": vulnerability['PublishedDate'] if 'PublishedDate' in vulnerability else None,
                                    "LastModifiedDate": vulnerability['LastModifiedDate'] if 'LastModifiedDate' in vulnerability else None,
                                    "InstalledVersion": vulnerability['InstalledVersion'],
                                    "FixedVersion": vulnerability['FixedVersion'] if 'FixedVersion' in vulnerability else None,
                                    "Severity": vulnerability['Severity'],
                                    "SeveritySource": vulnerability['SeveritySource'] if 'SeveritySource' in vulnerability else None,
                                    "Target": issue['Type'] if issue['Type'] in issue['Target'] else issue['Target'],
                                    "Modules": [module],
                                }
                            else:
                                if not module in cves[vulnerability['VulnerabilityID']]['Modules']:
                                    cves[vulnerability['VulnerabilityID']]['Modules'].append(module)

    logger.info(f"Found {len(cves)} vulnerabilities: ")

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), tag + "_cves.json"), "w") as f:
        json.dump(cves, f, indent=4)

    logger.info(f"Saved to {os.path.join(os.path.dirname(os.path.abspath(__file__)), tag + '_cvess.json')}")
