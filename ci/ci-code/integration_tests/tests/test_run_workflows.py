import logging
import time

import pytest
from integration_tests.utils.logger import get_logger
from integration_tests.workflows import WorkflowEndpoints

logger = get_logger(__name__, logging.INFO)


def wait_for_workflows(
    kaapana: WorkflowEndpoints, wait_for: list, timeout=3600
) -> tuple:
    """
    Block until all prerequisite workflows have finished successfully.

    Each entry in wait_for is either a plain dag_id string or a dict:
        dag_id:   str   - name of the prerequisite DAG
        min_jobs: int   - minimum number of jobs expected (default 1)

    The workflow_name queried is "ci_<dag_id>".  All jobs sharing that name
    must be in "finished" state and their count must reach min_jobs.
    """
    start_time = time.time()

    requirements = []
    for item in wait_for:
        if isinstance(item, str):
            requirements.append({"workflow_name": f"ci_{item}", "min_jobs": 1})
        else:
            requirements.append(
                {
                    "workflow_name": f"ci_{item['dag_id']}",
                    "min_jobs": item.get("min_jobs", 1),
                }
            )

    while abs(start_time - time.time()) < timeout:
        all_done = True
        for req in requirements:
            try:
                jobs_info = kaapana.get_jobs_info(workflow_name=req["workflow_name"])
            except Exception:
                all_done = False
                break

            jobs_status = [job.get("status") for job in jobs_info]

            if len(jobs_info) < req["min_jobs"]:
                all_done = False
                break

            if "failed" in jobs_status:
                return False, f"Prerequisite workflow {req['workflow_name']} failed: {jobs_info}"

            if not all(s == "finished" for s in jobs_status):
                all_done = False
                break

        if all_done:
            return True, "All prerequisite workflows succeeded"

        time.sleep(5)

    return False, f"Prerequisite workflows {[r['workflow_name'] for r in requirements]} exceeded timeout {timeout}s"


def wait_for_workflow(kaapana: WorkflowEndpoints, workflow_name, timeout=3600) -> tuple:
    """
    Check the status of all jobs in workflow <workflow_name> until all jobs finished, the run-time exceeds self.timeout or a single job failed.
    """
    start_time = time.time()
    jobs_info = []
    while abs(start_time - time.time()) < timeout:
        try:
            jobs_info = kaapana.get_jobs_info(workflow_name=workflow_name)
        except:
            pass
        jobs_status = [job.get("status") for job in jobs_info]
        logger.debug(f"jobs_info: {jobs_status}")
        if "failed" in jobs_status:
            msg = f"Workflow {workflow_name} failed: {jobs_info}"
            return False, msg
        elif jobs_status and jobs_status == ["finished" for _ in jobs_info]:
            msg = f"Workflow {workflow_name} succeeded."
            return True, msg
        else:
            time.sleep(5)
    msg = f"Workflow {workflow_name} exceeds timeout {timeout}"
    return False, msg


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

    ### Wait for prerequisite workflows before triggering
    wait_for = testcase.get("wait_for", [])
    if wait_for:
        logger.info(f"Waiting for prerequisite workflows: {wait_for}")
        success, msg = wait_for_workflows(kaapana, wait_for)
        if not success:
            pytest.fail(msg)
        logger.info(msg)

    ### Trigger the workflow
    try:
        response = kaapana.submit_workflow(testcase)
    except Exception as e:
        logger.error(f"Failed triggering workflow {testcase=} {e=}")
        raise e
    workflow_name = response["workflow_name"]
    logger.info(f"Workflow {workflow_name} started for dag {dag_id}.")
    ### Wait for workflow to finish
    success, msg = wait_for_workflow(kaapana, workflow_name)
    assert success
    logger.info(msg)
