"""
This script implements functions that make requests to the Gitlab REST API.
The functions in this module are used to create an issue in the current sprint with a link to the failed pipeline.
"""

from collections import defaultdict
import io
import json
import os
from pathlib import Path
from typing import Dict, List
import zipfile
import gitlab
from datetime import datetime, timezone

import gitlab.v4
import gitlab.v4.objects
import requests


def create_title(project: gitlab.v4.objects.Project, commit_sha: str) -> str:
    """
    Creates a title string for the issue. String consists of short commit hash and count of how many days since the issue was created.
    """
    days_since_commit = get_days_since_commit(project, commit_sha)
    return f"CI failed for commit {commit_sha} - Issue happening since {days_since_commit} Days"


def get_days_since_commit(project: gitlab.v4.objects.Project, commit_sha: str) -> int:
    """
    Returns the number of days since the specified commit was made.

    Args:
        project (gitlab.v4.objects.Project): The GitLab project to retrieve the commit from.
        commit_sha (str): The SHA of the commit to retrieve.

    Returns:
        int: The number of days since the commit was made.
    """
    commit = project.commits.get(commit_sha)
    commit_time = datetime.strptime(commit.committed_date, "%Y-%m-%dT%H:%M:%S.%f%z")
    days_since_commit = (datetime.now(timezone.utc) - commit_time).days
    return days_since_commit


def get_artifacts_dict(artifacts_dir: str) -> Dict[str, str]:
    artifacts_dict = {}
    for filename in Path(artifacts_dir).glob("*.log"):
        with open(filename, "r") as f:
            content = f.readlines()
        artifacts_dict[filename.name] = content
    return artifacts_dict


def filter_logs_by_keywords(
    logs: List[str], error_keywords: List[str], whitelist: List[str], context_lines: int
) -> str:
    seen_lines = set()
    filtered_logs = []
    for i, line in enumerate(logs):
        # Check if line contains error keywords but NOT whitelisted phrases
        if any(keyword in line.lower() for keyword in error_keywords) and not any(
            phrase in line for phrase in whitelist
        ):
            start = max(0, i - context_lines)
            end = min(len(logs), i + context_lines + 1)

            # Add only new lines (avoid duplicates)
            for j in range(start, end):
                if j not in seen_lines:
                    filtered_logs.append(logs[j])
                    seen_lines.add(j)  # Mark this line as added

    filtered_logs_str = "".join(filtered_logs)
    return filtered_logs_str


def get_ai_model_data(api_key):
    headers = {"accept": "application/json", "Authorization": f"Bearer {api_key}"}
    url = "https://helmholtz-blablador.fz-juelich.de:8000/v1/models"
    response = requests.get(url=url, headers=headers)
    return response.json()["data"]


def submit_ai_request(messages: List[Dict[str, str]], model: str, token: str):
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "top_p": 0,
        "n": 1,
        "max_tokens": 65000,
        "stop": ["string"],
        "stream": "false",
        "presence_penalty": 0.5,
        "frequency_penalty": 0.5,
        "user": "kaapana-ci",
    }
    payload = json.dumps(payload)
    url = "https://helmholtz-blablador.fz-juelich.de:8000/v1/chat/completions"

    response = requests.post(url=url, headers=headers, data=payload)
    response.raise_for_status()
    return response


def create_ai_report(
    error_logs_report: str,
    token: str,
) -> str:
    try:
        model = get_ai_model_data(token)[0]["id"]

        instructions = [
            {
                "role": "user",
                "content": "\n".join(
                    [
                        "Use the logs provided to create a report in markdown separated into 2 parts.",
                        "First part will summarize the potential cause of the error found in the logs, add relevant part of the log and add it in as markdown code block.",
                        "Second part will summarize potential fixes and solutions to the problem.",
                        "Use only 3rd and lower header level so ### and lower.",
                        "Keep Report consise, brief and as robust as possible.",
                    ]
                ),
            },
            {
                "role": "user",
                "content": error_logs_report,
            },
        ]

        response = submit_ai_request(instructions, model, token)
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print("AI logs analysis was not successfull. Skipping.")
    return "AI report failed"


def create_failed_jobs_report(failed_jobs: List[gitlab.v4.objects.ProjectPipelineJob]):
    """
    Retrieves failed jobs from a pipeline.

    Args:
        project (gitlab.v4.objects.Project): The GitLab project object.
        ci_pipeline_id (int): The ID of the pipeline to retrieve failed jobs from.

    Returns:
        Tuple[str, str]: A tuple containing the failed jobs string and an empty string.
    """
    if not failed_jobs:
        return ("No failed jobs found in the pipeline.",)

    failed_jobs_strs = [f"- Job {job.id}: {job.name} (Failed)" for job in failed_jobs]
    return "\n".join(failed_jobs_strs)


def extract_error_logs(
    artifacts_dir: str,
) -> Dict[str, Dict[str, str]]:
    artifacts_dict = get_artifacts_dict(artifacts_dir)
    error_logs = {}
    for filename, content in artifacts_dict.items():
        # Phrases that should be considered error lines
        error_keywords = ["error", "failed", "exception", "fatal", "critical"]

        # Phrases that should NOT be considered error lines
        whitelist = [
            "exit_on_error",
            "vulnerability_severity_level='CRITICAL,HIGH'",
            "faq"
        ]

        context_lines = 3  # Number of surrounding lines to include
        error_logs[filename] = filter_logs_by_keywords(
            content,
            error_keywords=error_keywords,
            whitelist=whitelist,
            context_lines=context_lines,
        )
    return error_logs


def create_error_logs_report(error_logs: Dict[str, Dict[str, str]]) -> str:
    """
    Generates a formatted report of extracted error logs.

    Args:
        error_logs (Dict[str, Dict[str, str]]): A dictionary where keys are job names,
        and values are dictionaries mapping filenames to filtered log contents.

    Returns:
        str: A formatted string containing the error logs report.
    """
    report_lines = []

    if not error_logs:
        return "No error logs found."

    for filename, content in error_logs.items():
        report_lines.append(f"### File: {filename}\n")
        report_lines.append("```log")
        report_lines.append(
            content.strip()
            if content
            else "_No relevant log entries found._"
        )
        report_lines.append("```\n")

    return "\n".join(report_lines)


def create_description(
    project: gitlab.v4.objects.Project,
    ci_pipeline_url: str,
    ci_pipeline_id: str,
    registry_token: str,
    artifacts_dir: str,
):
    failed_jobs = project.pipelines.get(ci_pipeline_id).jobs.list(scope="failed")
    failed_jobs_report = create_failed_jobs_report(failed_jobs)

    error_logs = extract_error_logs(artifacts_dir)
    error_logs_report = create_error_logs_report(error_logs)
    ai_report = create_ai_report(error_logs_report, registry_token)
    description = f"""
# CI pipeline failed

## Pipeline Details

[View Pipeline]({ci_pipeline_url})

## Failed Jobs

{failed_jobs_report}
   
## Collected Error Logs

{error_logs_report}
    
## AI Report
    
{ai_report}

---
*This issue was auto-generated by the CI monitoring system.*
"""

    return description


def create_issue_for_commit(
    project: gitlab.v4.objects.Project,
    registry_token: str,
    ci_pipeline_url: str,
    ci_pipeline_id: int,
    commit_sha: str,
    artifacts_dir: str,
) -> gitlab.v4.objects.ProjectIssue:
    """Creates a new issue for a commit when a CI pipeline fails.

    Args:
        gl (gitlab.Gitlab): GitLab API client.
        project_id (str): The project ID to create the issue in.
        ci_pipeline_url (str): The URL of the failed CI pipeline.
        commit_sha (str): The commit SHA associated with the failed pipeline.

    Returns:
        gitlab.v4.objects.ProjectIssue: The created issue object.
    """

    issue_title = create_title(project, commit_sha)
    issue_description = create_description(
        project=project,
        registry_token=registry_token,
        ci_pipeline_id=ci_pipeline_id,
        ci_pipeline_url=ci_pipeline_url,
        artifacts_dir=artifacts_dir,
    )

    with open("test.md", "w+") as f:
        f.writelines(issue_description)

    issue = {
        "title": issue_title,
        "labels": ["CI", "Sprint"],
        "description": issue_description,
    }
    # return project.issues.create(issue)


def update_issue_title(
    project: gitlab.v4.objects.Project,
    issue: gitlab.v4.objects.ProjectIssue,
    commit_sha: str,
) -> gitlab.v4.objects.ProjectIssue:
    """Updates the title of an existing issue based on the commit's timestamp.

    Args:
        gl (gitlab.Gitlab): GitLab API client.
        project_id (str): The project ID where the issue resides.
        issue (gitlab.v4.objects.ProjectIssue): The existing issue object to update.
        commit_sha (str): The commit SHA associated with the failed pipeline.

    Returns:
        None
    """
    issue.title = create_title(project, commit_sha)
    issue.save()


def main():
    registry_token = os.getenv("REGISTRY_TOKEN")
    project_id = os.getenv("CI_PROJECT_ID")
    ci_pipeline_url = os.getenv("CI_PIPELINE_URL")
    ci_pipeline_id = os.getenv("CI_PIPELINE_ID")
    commit_sha = os.getenv("CI_COMMIT_SHA_SHORT")
    artifacts_dir = os.getenv("ARTIFACTS_DIR")

    gl = gitlab.Gitlab(
        url="https://codebase.helmholtz.cloud",
        private_token=registry_token,
        ssl_verify=False,
    )

    project_kaapana = gl.projects.get(id=project_id)
    existing_issues = project_kaapana.issues.list(
        state="opened", labels=["CI", "Sprint"], search=commit_sha
    )
    if not existing_issues:
        issue = create_issue_for_commit(
            project=project_kaapana,
            ci_pipeline_url=ci_pipeline_url,
            ci_pipeline_id=ci_pipeline_id,
            commit_sha=commit_sha,
            registry_token=registry_token,
            artifacts_dir=artifacts_dir,
        )

    else:
        issue = update_issue_title(project_kaapana, existing_issues[0], commit_sha)
    # issue.save()


if __name__ == "__main__":
    main()
