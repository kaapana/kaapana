import logging
import time

import pytest
from integration_tests.utils.logger import get_logger
from integration_tests.utils.pod_logs import fetch_failed_pod_logs
from integration_tests.workflows import WorkflowEndpoints

logger = get_logger(__name__, logging.INFO)


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
            namespace = kaapana.admin_project.get("kubernetes_namespace")
            logger.error(fetch_failed_pod_logs(namespace))
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
