import fnmatch
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import gitlab
import gitlab.v4.objects
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("mr_review")

MODEL = "alias-fast"
MARKER = "<!-- kaapana-mr-review -->"
INSTRUCTIONS = Path(__file__).with_name("instructions.md")
DIFF_BUDGET = 200000
ISSUE_BUDGET = 10000
MAX_ISSUES = 5
BRANCH_ISSUE = re.compile(r"^(?:[^/]+/)?(\d+)-")
EXCLUDED = (
    "*.lock",
    "*-lock.json",
    "*-lock.yaml",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.svg",
    "*.png",
    "*.jpg",
    "*.ico",
    "*.pdf",
)


def submit_ai_request(messages: List[Dict[str, str]], model: str, token: str) -> requests.Response:
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
        "max_tokens": 8000,
        "stream": False,
        "user": "kaapana-ci",
    }
    url = "https://api.helmholtz-blablador.fz-juelich.de/v1/chat/completions"

    response = requests.post(url=url, headers=headers, data=json.dumps(payload), timeout=900)
    response.raise_for_status()
    return response


def create_ai_review(mr_report: str, token: str) -> Optional[str]:
    try:
        instructions = [
            {"role": "system", "content": INSTRUCTIONS.read_text()},
            {"role": "user", "content": mr_report},
        ]
        response = submit_ai_request(instructions, MODEL, token)
        ai_review = response.json()["choices"][0]["message"]["content"]
        ai_review = re.sub(r"<think>.*?</think>", "", ai_review or "", flags=re.DOTALL).strip()
        if ai_review:
            return ai_review
    except Exception as e:
        logger.error(f"AI review was not successfull: {e}. Skipping.")
    return None


def is_excluded(path: str) -> bool:
    return any(fnmatch.fnmatch(Path(path).name, pattern) for pattern in EXCLUDED)


def create_diff_report(diffs: List[Dict]) -> Tuple[str, List[str]]:
    parts, skipped, used = [], [], 0
    for change in diffs:
        path = change["new_path"]
        if change.get("deleted_file"):
            skipped.append(f"{path} (deleted)")
            continue
        if is_excluded(path) or change.get("too_large") or not change.get("diff"):
            skipped.append(f"{path} (generated, binary or too large)")
            continue
        chunk = f"--- a/{change['old_path']}\n+++ b/{path}\n{change['diff']}"
        if used + len(chunk) > DIFF_BUDGET:
            skipped.append(f"{path} (over the diff budget)")
            continue
        parts.append(chunk)
        used += len(chunk)
    return "\n".join(parts), skipped


def get_linked_issues(project: gitlab.v4.objects.Project, mr: gitlab.v4.objects.ProjectMergeRequest) -> List[Dict]:
    issues = {}
    for source in (mr.closes_issues, mr.related_issues):
        try:
            for issue in source():
                issues.setdefault(issue.web_url, issue.attributes)
        except gitlab.exceptions.GitlabError as e:
            logger.warning(f"Could not list linked issues: {e}")
    match = BRANCH_ISSUE.match(mr.source_branch)
    if match:
        try:
            issue = project.issues.get(match.group(1))
            issues.setdefault(issue.web_url, issue.attributes)
        except gitlab.exceptions.GitlabGetError:
            logger.info(f"No issue #{match.group(1)} for branch {mr.source_branch}")
    return list(issues.values())[:MAX_ISSUES]


def create_issues_report(issues: List[Dict]) -> List[str]:
    if not issues:
        return ["Linked issues: none. No issue is linked to this merge request.", ""]
    lines = ["Linked issues:"]
    for issue in issues:
        description = (issue.get("description") or "(empty)")[:ISSUE_BUDGET]
        reference = issue.get("references", {}).get("full") or f"#{issue['iid']}"
        lines += [
            "",
            f"Issue {reference} ({issue['state']}): {issue['title']}",
            "```text",
            description,
            "```",
        ]
    return lines + [""]


def create_mr_report(
    mr: gitlab.v4.objects.ProjectMergeRequest, issues: List[Dict], diff: str, skipped: List[str]
) -> str:
    lines = [
        f"Title: {mr.title}",
        f"Source branch: {mr.source_branch} -> {mr.target_branch}",
        "",
        "Description:",
        mr.description or "(empty)",
        "",
        *create_issues_report(issues),
    ]
    if skipped:
        lines += ["Files not included in the diff:", *[f"- {item}" for item in skipped], ""]
    lines += ["Diff:", "```diff", diff, "```"]
    return "\n".join(lines)


def neutralize(text: str) -> str:
    text = re.sub(r"(?m)^(\s*)/", r"\1\\/", text)
    return re.sub(r"@(?=[\w-])", "@\u200b", text)


def find_review_note(
    mr: gitlab.v4.objects.ProjectMergeRequest, user_id: int
) -> Optional[gitlab.v4.objects.ProjectMergeRequestNote]:
    for note in mr.notes.list(iterator=True):
        if note.author["id"] == user_id and MARKER in note.body:
            return note
    return None


def main():
    gitlab_api_token = os.getenv("GITLAB_API_TOKEN")
    blablador_token = os.getenv("BLABLADOR_API_TOKEN")
    project_id = os.getenv("CI_MERGE_REQUEST_PROJECT_ID")
    mr_iid = os.getenv("CI_MERGE_REQUEST_IID")
    commit_sha = os.getenv("CI_COMMIT_SHA")
    ci_job_url = os.getenv("CI_JOB_URL")

    gl = gitlab.Gitlab(
        url="https://codebase.helmholtz.cloud",
        private_token=gitlab_api_token,
        ssl_verify=True,
    )
    gl.auth()

    project_kaapana = gl.projects.get(id=project_id)
    mr = project_kaapana.mergerequests.get(mr_iid)

    note = find_review_note(mr, gl.user.id)
    if note and os.getenv("MR_REVIEW_FORCE") != "true":
        logger.info("Merge request already reviewed. Run mr_review_rerun for a new review. Skipping.")
        return

    diffs = gl.http_list(f"/projects/{project_kaapana.id}/merge_requests/{mr.iid}/diffs", get_all=True)
    diff, skipped = create_diff_report(diffs)
    if not diff:
        logger.info("No reviewable changes. Skipping.")
        return

    issues = get_linked_issues(project_kaapana, mr)
    logger.info(f"Reviewing {len(diffs)} files and {len(issues)} linked issues at {commit_sha[:8]} with {MODEL}")
    ai_review = create_ai_review(create_mr_report(mr, issues, diff, skipped), blablador_token)
    if ai_review is None:
        sys.exit(1)

    body = "\n".join(
        [
            MARKER,
            "### 🤖 Automated review",
            "",
            neutralize(ai_review),
            "",
            "---",
            f"<sub>{MODEL} via Blablador on {commit_sha} · advisory only · [job]({ci_job_url})</sub>",
        ]
    )
    if note:
        note.body = body
        note.save()
        logger.info(f"Updated note {note.id}")
    else:
        note = mr.notes.create({"body": body})
        logger.info(f"Created note {note.id}")


if __name__ == "__main__":
    main()
