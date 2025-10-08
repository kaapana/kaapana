import pytest
import asyncio
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
    kaapana = WorkflowEndpoints(host=host, client_secret=client_secret)
    assert client_secret, "No client secret specified!"
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


@pytest.mark.asyncio
@pytest.mark.usefixtures("testconfig")
async def test_workflow(testconfig):
    """
    A generic test method derived from a dag_id and a JSON string.
    """
    testcase, kaapana = testconfig

    dag_id = testcase.get("dag_id")
    if testcase.get("ci_ignore", False) == True:
        logger.info(f"Ignore testcase for {dag_id=}")
        return None
    ### Check that dag is available
    if dag_id not in kaapana.get_dags():
        logger.warning(f"DAG {dag_id=} not available on the platform!")
        logger.warning(f"Skip test!")
        return None
    ### Adjust payload/workflow_form before triggering the workflow
    testcase["workflow_name"] = "ci_" + dag_id
    logger.info(f"Start testcase for {dag_id=}")
    instance_names = testcase.get("instance_names", [])
    if host not in instance_names:
        instance_names.append(host)
        testcase["instance_names"] = instance_names
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
