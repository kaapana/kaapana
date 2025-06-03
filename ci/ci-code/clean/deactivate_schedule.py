"""
This module implements functions that make requests to the Gitlab REST API.
The functions in this module are used to deactivate a schedule by the pipeline id of the last pipeline triggered by this schedule.
"""
import requests
import argparse
import sys

def parser():
    p = argparse.ArgumentParser(usage="Deactivate a schedule given the pipeline id of the last pipeline triggered by this schedule.")
    p.add_argument("--last-pipeline-id", required=True, type=int, help="Last pipeline id of the schedule to be deactivated.")
    p.add_argument("--api-token", required=True, help="Project token with API scope")
    p.add_argument("--project-id", required=True, help="Project id of the gitlab project")
    p.add_argument("--gitlab-host", required=True, help="Gitlab host e.g. https://gitlab.example.com")
    return p.parse_args()

def main():
    args = parser()
    last_pipeline_id = int(args.last_pipeline_id)
    project_id = args.project_id
    gitlab_host = args.gitlab_host
    api_token = args.api_token

    schedules = get_schedules(project_id, gitlab_host, api_token)
    schedule_deactivated = None
    print(schedules)
    for schedule in schedules:
        schedule_id = schedule["id"]
        schedule = get_schedule(schedule_id, project_id, gitlab_host, api_token)
        last_pipeline_of_schedule = schedule["last_pipeline"]["id"]

        if last_pipeline_id == last_pipeline_of_schedule:
            print(f"Schedule deactivated for schedule id: {schedule_id}")
            schedule_deactivated = deactivate_schedule(schedule_id, project_id, gitlab_host, api_token)

    if schedule_deactivated:
        sys.exit(0)

    print("No schedule found for the specified pipeline id.")
    sys.exit(1)

def get_schedules(project_id, gitlab_host, api_token):
    """
    Call to the gitlab REST-API to receive a list of all available schedules.
    """
    headers = {'PRIVATE-TOKEN': api_token}     
    r = requests.get(f"{gitlab_host}/api/v4/projects/{project_id}/pipeline_schedules",
    headers=headers)
    r.raise_for_status()
    return r.json()

def get_schedule(schedule_id, project_id, gitlab_host, api_token):
    """
    Call to the gitlab REST-API to receive the information on the schedule with id schedule_id
    """
    headers = {'PRIVATE-TOKEN': api_token}
    r = requests.get(f"{gitlab_host}/api/v4/projects/{project_id}/pipeline_schedules/{schedule_id}",
    headers=headers
    )
    r.raise_for_status()
    return r.json()

def deactivate_schedule(schedule_id, project_id, gitlab_host, api_token):
    """
    Call to the gitlab REST-API to deactivate a schedule
    """
    headers = {'PRIVATE-TOKEN': api_token}
    payload = {"active": "false"}
    r = requests.put(f"{gitlab_host}/api/v4/projects/{project_id}/pipeline_schedules/{schedule_id}",
    headers=headers,
    data=payload
    )
    r.raise_for_status()
    resp = r.json()
    assert resp["active"] == False
    return True

if __name__== "__main__":
    main()