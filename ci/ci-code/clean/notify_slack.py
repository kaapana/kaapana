import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Load secrets from environment variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

# Initialize Slack client
client = WebClient(token=SLACK_BOT_TOKEN)


def send_message(message: str):
    """Sends a message to the fixed Slack channel."""
    try:
        response = client.chat_postMessage(channel=SLACK_CHANNEL_ID, text=message)
        return response
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")


# Example usage
if __name__ == "__main__":

    message = """Dear Kaapana developers, 
    unfortunately a CI pipeline failed for branch: {}. Here is a link to the pipeline: {}."""
    ci_pipeline_url = os.getenv("CI_PIPELINE_URL")
    ci_commit_branch = os.getenv("CI_COMMIT_BRANCH")

    send_message(message.format(ci_commit_branch, ci_pipeline_url))
