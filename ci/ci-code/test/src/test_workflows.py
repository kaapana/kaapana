import pytest
import os
from base_utils.utils_workflows import (
    collect_all_testcases,
    read_payload_from_yaml,
    WorkflowEndpoints,
)
import time
from base_utils.logger import get_logger
import logging

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
            return False, msg
        elif jobs_status and jobs_status == ["finished" for _ in jobs_info]:
            msg = f"Workflow {workflow_name} succeeded."
            return True, msg
        else:
            time.sleep(5)
    msg = f"Workflow {workflow_name} exceeds timeout {timeout}"
    return False, msg


def pytest_generate_tests(metafunc):
    host = metafunc.config.getoption("host")
    assert host, "No host specified!"
    client_secret = metafunc.config.getoption("client_secret") or os.environ.get(
        "CLIENT_SECRET", None
    )
    assert client_secret, "No client secret specified!"
    kaapana = WorkflowEndpoints(host=host, client_secret=client_secret)
    if "testconfig" in metafunc.fixturenames:

        files = metafunc.config.getoption("files")
        test_dir = metafunc.config.getoption("test_dir")

        if files and len(files) != 0:
            testcases = []
            for file in files:
                testcases += read_payload_from_yaml(file)
        elif test_dir:
            testdir = os.path.join(os.getcwd(), test_dir)
            testcases = collect_all_testcases(testdir)
        else:
            raise AssertionError("Use --files or --test-dir to specify testcase files")
        metafunc.parametrize("testconfig", [(tc, kaapana) for tc in testcases])


def set_task_form_environment(env_name: str, env_value: str, testcase: dict):
    """
    Set in all tasks the values of environment variable env_name to env_value.
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
@pytest.mark.usefixtures("testconfig")
async def test_workflow(testconfig):
    """
    A generic test method derived from a dag_id and a JSON string.
    """
    testcase, kaapana = testconfig

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
        logger.error(f"Failed triggering workflow {testcase=}")
        raise e
    workflow_name = response["workflow_name"]
    logger.info(f"Workflow {workflow_name} started for dag {dag_id}.")
    ### Wait for workflow to finish
    success, msg = wait_for_workflow(kaapana, workflow_name)
    assert success
    logger.info(msg)
