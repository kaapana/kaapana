import logging
import time

import pytest
from integration_tests.utils.logger import get_logger
from integration_tests.workflows import WorkflowEndpoints

logger = get_logger(__name__, logging.INFO)

CLEANER_TASK_ID = "workflow-cleaner"


def wait_for_workflow(
    kaapana: WorkflowEndpoints, workflow_name, timeout=3600, expected_status="finished"
) -> tuple:
    """
    Poll the jobs in workflow <workflow_name> until they all reach a terminal state
    (finished/failed), the run-time exceeds timeout, or a job reaches an unexpected
    terminal state. Returns (True, msg) only if every job ends in expected_status.
    """
    start_time = time.time()
    jobs_info = []
    while abs(start_time - time.time()) < timeout:
        try:
            jobs_info = kaapana.get_jobs_info(workflow_name=workflow_name)
        except Exception as e:
            logger.warning(f"Could not fetch jobs for {workflow_name}: {e}")
        jobs_status = [job.get("status") for job in jobs_info]
        logger.debug(f"jobs_info: {jobs_status}")
        if jobs_status and all(
            status in ("finished", "failed", "deleted") for status in jobs_status
        ):
            if all(status == expected_status for status in jobs_status):
                msg = f"Workflow {workflow_name} reached expected status {expected_status!r}."
                return True, msg
            msg = (
                f"Workflow {workflow_name} reached {jobs_status}, "
                f"expected all jobs in {expected_status!r}: {jobs_info}"
            )
            return False, msg
        time.sleep(5)
    msg = f"Workflow {workflow_name} exceeds timeout {timeout}"
    return False, msg


def assert_cleanup_ran(kaapana: WorkflowEndpoints, workflow_name):
    """
    Assert that the workflow-cleaner task succeeded for every job in <workflow_name>,
    regardless of whether the workflow itself succeeded or failed.
    """
    jobs_info = kaapana.get_jobs_info(workflow_name=workflow_name)
    assert jobs_info, f"No job info found for workflow {workflow_name}"
    for job in jobs_info:
        task_instances = kaapana.get_job_taskinstances(job["id"])
        cleaner_state = task_instances.get(CLEANER_TASK_ID)
        assert cleaner_state is not None, (
            f"No {CLEANER_TASK_ID!r} task instance found for job {job['id']} "
            f"of workflow {workflow_name}"
        )
        assert cleaner_state[1] == "success", (
            f"Expected {CLEANER_TASK_ID!r} to succeed regardless of workflow outcome, "
            f"got state {cleaner_state[1]!r} for job {job['id']} of workflow {workflow_name}"
        )


def set_task_form_environment(env_name: str, env_value: str, testcase: dict):
    """
    Set the values of the environment variable env_name to env_value in all tasks.
    """
    if task_form := testcase["conf_data"].get("task_form"):
        for task_id, task_config in task_form.items():
            for i, env in enumerate(task_config.get("env", [])):
                print(i, env)
                if env["name"] == env_name:
                    copied_env = testcase["conf_data"]["task_form"][task_id][
                        "env"
                    ].copy()
                    copied_env.pop(i)
                    copied_env.append(
                        {
                            "name": env_name,
                            "value": env_value,
                        }
                    )
                    testcase["conf_data"]["task_form"][task_id]["env"] = copied_env
                    break
                else:
                    continue
    return testcase


 
@pytest.mark.asyncio
async def test_workflow(workflow_endpoints: WorkflowEndpoints, testconfig):
    """
    A generic test method derived from a dag_id and a JSON string.
    """
    kaapana = workflow_endpoints
    testcase = testconfig

    dag_id = testcase.get("dag_id")
    if testcase.get("ci_ignore", False):
        logger.info(f"Ignore testcase for {dag_id=}")
        return None
    ### Check that dag is available
    if dag_id not in kaapana.get_dags():
        logger.warning(f"DAG {dag_id=} not available on the platform!")
        logger.warning("Skip test!")
        return None
    ### Adjust payload/workflow_form before triggering the workflow
    testcase["workflow_name"] = "ci_" + dag_id
    logger.info(f"Start testcase for {dag_id=}")
    instance_names = testcase.get("instance_names", [])
    if kaapana.host not in instance_names:
        instance_names.append(kaapana.host)
        testcase["instance_names"] = instance_names

    ### Adjust KAAPANA_PROJECT_IDENTIFIER in conf_data.task_form.<task_id>
    for name, value in [
        ("KAAPANA_PROJECT_IDENTIFIER", kaapana.admin_project.get("id"))
    ]:
        testcase = set_task_form_environment(
            env_name=name, env_value=value, testcase=testcase
        )

    ### Trigger the workflow
    try:
        response = kaapana.submit_workflow(testcase)
    except Exception as e:
        logger.error(f"Failed triggering workflow {testcase=} {e=}")
        raise e
    workflow_name = response["workflow_name"]
    logger.info(f"Workflow {workflow_name} started for dag {dag_id}.")
    ### Wait for workflow to finish
    expected_status = testcase.get("expected_status", "finished")
    success, msg = wait_for_workflow(
        kaapana, workflow_name, expected_status=expected_status
    )
    assert success, msg
    logger.info(msg)

    if testcase.get("assert_cleanup", False):
        assert_cleanup_ran(kaapana, workflow_name)
