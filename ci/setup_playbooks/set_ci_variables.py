"""
You have to give a path to the config file as the first argument.
"""

import requests
from yaml import load, Loader
import argparse
import sys


def parser():
    p = argparse.ArgumentParser()
    p.add_argument("file", help="Path to config file")
    p.add_argument("--api-token", help="Project api-token", default=False)
    p.add_argument("--project-id", default="2521")
    p.add_argument("--gitlab-host", help="Gitlab host e.g. https://gitlab.example.com")
    return p.parse_args()


def main():
    args = parser()
    print(args)
    file = args.file
    project_id = args.project_id
    api_token = args.api_token
    gitlab_host = args.gitlab_host
    with open(file) as f:
        config = load(f, Loader=Loader)
        if project_id and api_token and gitlab_host:
            upload_to_gitlab(config, project_id, api_token, gitlab_host)
        else:
            print(
                f"You have to specify values for --api-token --project-id and --gitlab-host."
            )
            sys.exit(1)


def upload_to_gitlab(config, project_id, api_token, gitlab_host):
    headers = {"PRIVATE-TOKEN": api_token}
    for key, value in config.items():
        r = requests.post(
            f"{gitlab_host}/api/v4/projects/{project_id}/variables",
            headers=headers,
            files=set_files(key, value),
        )
        print(r.text)


def set_files(key, value):
    files = {"key": (None, key), "value": (None, value)}
    return files


if __name__ == "__main__":
    main()
