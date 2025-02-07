"""
This script implements functions that make requests to the Gitlab REST API.
The functions in this module are used to create an issue in the current sprint with a link to the failed pipeline.
"""

import gitlab
import os

issue_description_template = """# CI pipeline failed
[Pipeline details]({})
"""
issue_template = {
    "title": "CI failed for develop branch",
    "labels": ["CI", "Sprint"],
    "description": issue_description_template,
}


def main():
    registry_token = os.getenv("REGISTRY_TOKEN")
    project_id = os.getenv("CI_PROJECT_ID")
    ci_pipeline_url = os.getenv("CI_PIPELINE_URL")
    gl = gitlab.Gitlab(
        url="https://codebase.helmholtz.cloud",
        private_token=registry_token,
        ssl_verify=False,
    )

    issue_template["description"] = issue_description_template.format(ci_pipeline_url)

    project_kaapana = gl.projects.get(id=project_id)
    issue = project_kaapana.issues.create(issue_template)
    issue.save()


if __name__ == "__main__":
    main()
