#!/usr/bin/env python3
import sys
import json
import uuid
from datetime import datetime


def convert_vulnerability_report_to_gitlab(security_report):
    gitlab_report = {
        "version": "2.0",
        "scan": {
            "scanner": {
                "id": "trivy",
                "name": "Trivy",
                "url": "https://github.com/aquasecurity/trivy/",
                "vendor": {"name": "GitLab"},
                "version": "0.26.0",
            },
            "analyzer": {
                "id": "gcs",
                "name": "GitLab Container Scanning",
                "vendor": {"name": "GitLab"},
                "version": "5.1.0",
            },
            "type": "container_scanning",
            "start_time": "2022-05-19T12:47:33",
            "end_time": "2022-05-19T12:47:42",
            "status": "success",
        },
        "vulnerabilities": [],
    }

    for cve, vulnerability in security_report.items():
        gitlab_vuln = {
            "id": str(uuid.uuid4()),
            "category": "container_scanning",
            "message": vulnerability.get("Title") or cve,
            "description": "TODO",
            "severity": vulnerability.get("Severity", "Unknown"),
            "confidence": "High",
            "scanner": {"id": "trivy", "name": "Trivy"},
            "location": {
                "dependency": {
                    "package": {"name": vulnerability.get("PkgName")},
                    "version": vulnerability.get("InstalledVersion"),
                },
                "operating_system": "TODO",
                "image": ";".join(vulnerability.get("Modules", ["unknown"])),
            },
            "identifiers": [
                {
                    "type": "cve",
                    "name": cve,
                    "value": cve,
                }
            ],
        }
        gitlab_report["vulnerabilities"].append(gitlab_vuln)

    return gitlab_report


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: convert_trivy_to_gitlab.py <vulnerability-report-json-file>",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = sys.argv[1]
    try:
        with open(input_path, "r") as f:
            trivy_data = json.load(f)
    except FileNotFoundError:
        trivy_data = []

    gitlab_data = convert_vulnerability_report_to_gitlab(trivy_data)
    print(json.dumps(gitlab_data, indent=2))


if __name__ == "__main__":
    main()
