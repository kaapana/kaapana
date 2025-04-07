import os

import gitlab
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def send_message(client: WebClient, channel: str, message: str):
    """Sends a message to a given Slack channel."""
    try:
        response = client.chat_postMessage(channel=channel, text=message)
        return response
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")


def main():
    # Load secrets and env vars
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    slack_channel = os.getenv("SLACK_CHANNEL_ID")
    registry_token = os.getenv("REGISTRY_TOKEN")
    project_id = os.getenv("CI_PROJECT_ID")
    pipeline_url = os.getenv("CI_PIPELINE_URL")
    commit_sha = os.getenv("CI_COMMIT_SHORT_SHA")
    branch = os.getenv("CI_COMMIT_BRANCH")

    # Set up clients
    slack_client = WebClient(token=slack_token)
    gl = gitlab.Gitlab(
        url="https://codebase.helmholtz.cloud",
        private_token=registry_token,
        ssl_verify=False,
    )

    # Logic
    project = gl.projects.get(id=project_id)
    issues = project.issues.list(state="opened", labels=["CI"], search=commit_sha)

    if len(issues) == 1:
        issue_url = issues[0].web_url
        message = (
            "*Dear Kaapana developers*,\n\n"
            "Unfortunately, a *CI pipeline* has failed for branch: `{}`.\n"
            "*Pipeline:* <{}>\n"
            "*Issue:* <{}>\n"
        ).format(branch, pipeline_url, issue_url)
        send_message(slack_client, slack_channel, message)


if __name__ == "__main__":
    main()
