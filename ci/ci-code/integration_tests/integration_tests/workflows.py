import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import requests
from integration_tests.utils.KaapanaAuth import KaapanaAuth
from integration_tests.utils.logger import get_logger
from yaml import Loader, load_all

logger = get_logger(__name__, logging.INFO)


class WorkflowEndpoints(KaapanaAuth):
    def __init__(self, host, client_secret):
        super().__init__(host, client_secret)

    def submit_workflow(self, payload):
        """
        Submit a workflow to the kaapana-backend API.
        """
        logger.debug(payload)
        r = self.request(
            "kaapana-backend/client/workflow",
            request_type=requests.post,
            _json=payload,
            retries=1,
        )
        try:
            message = r.json()
        except json.decoder.JSONDecodeError as e:
            logger.error("Triggering the dag failed!")
            logger.error(r.text)
            raise e
        return message

    def get_dags(self) -> list:
        """
        Get a list of all DAGs installed on the platform
        """
        r = self.request(
            "kaapana-backend/client/dags?only_dag_names=true", request_type=requests.get
        )
        return r.json()

    def get_jobs_info(
        self, instance_name=None, workflow_name=None, status=None, limit=None
    ):
        """
        Get info about jobs from kaapana-backend API
        """
        params = {}
        if instance_name:
            params["instance_name"] = instance_name
        if workflow_name:
            params["workflow_name"] = workflow_name
        if status:
            params["status"] = status
        if limit:
            params["limit"] = limit
        r = self.request(
            "kaapana-backend/client/jobs", request_type=requests.get, params=params
        )
        return r.json()

    def trigger_multiple_testcases(self, testcases):
        """
        Trigger multiple dags from a list of testcases.
        """
        messages = []
        for form in testcases:
            message = self.submit_workflow(form)
            messages += message
        return messages


def read_payload_from_yaml(file_path):
    """
    Load dag run specific data from a yaml file.
    Translate this data into json strings.
    Output a list of tuples (dag_id, json-string)
    """
    testcases = []
    if os.stat(file_path).st_size == 0:
        return []

    with open(file_path) as f:
        for case in load_all(f, Loader=Loader):
            if case is not None:
                testcases.append(case)
    return testcases


def collect_testcase_files(testcase_dir):
    """
    Search through the testcase_dir and return all YAML files in a deterministic order.
    """
    list_of_yaml_files = sorted(Path(testcase_dir).rglob("*.yaml"))
    logger.debug(f"yaml files: {list_of_yaml_files}")
    return list_of_yaml_files


@dataclass(frozen=True)
class PlannedTestcase:
    """A testcase ready to be parametrized, with its distribution constraints."""

    payload: dict
    group: str
    step: str | None
    after: tuple[str, ...]


def plan_testcases(testcase_files: list[Path]) -> list[PlannedTestcase]:
    """
    Read the config files and order their testcases for distribution.

    A testcase names itself with ci_step and its prerequisites with ci_after.
    Testcases connected that way form one group, ordered so that prerequisites
    come first, which means the declaration decides the order rather than the
    position of a document in its file. Unconnected testcases each get a group
    of their own and are therefore distributed freely.

    Raise ValueError on a name declared twice, a reference to a name no
    collected testcase declares, or a cycle.
    """
    payloads: list[dict] = []
    steps: list[str | None] = []
    afters: list[tuple[str, ...]] = []
    origins: list[str] = []

    for file in testcase_files:
        for index, payload in enumerate(read_payload_from_yaml(file)):
            # ci_step and ci_after steer collection and must not reach the platform
            payloads.append(payload)
            steps.append(payload.pop("ci_step", None))
            afters.append(tuple(payload.pop("ci_after", ())))
            origins.append(f"{file.parent.parent.name}/{file.stem}#{index}")

    index_of_step: dict[str, int] = {}
    for index, step in enumerate(steps):
        if step is None:
            continue
        if step in index_of_step:
            raise ValueError(
                f"ci_step {step!r} is declared by {origins[index_of_step[step]]} "
                f"and by {origins[index]}, names must be unique"
            )
        index_of_step[step] = index

    dependents: dict[int, list[int]] = {index: [] for index in range(len(payloads))}
    for index, after in enumerate(afters):
        for name in after:
            if name not in index_of_step:
                raise ValueError(
                    f"{origins[index]} declares ci_after {name!r}, which no collected "
                    f"testcase declares as ci_step"
                )
            dependents[index_of_step[name]].append(index)

    component_of = _components(len(payloads), dependents)
    members: dict[int, list[int]] = {}
    for index, component in enumerate(component_of):
        members.setdefault(component, []).append(index)

    planned: list[PlannedTestcase] = []
    for component in dict.fromkeys(component_of):
        indices = members[component]
        names = sorted(steps[index] for index in indices if steps[index])
        group = names[0] if names else origins[indices[0]]
        for index in _prerequisites_first(indices, afters, dependents, origins):
            planned.append(
                PlannedTestcase(
                    payload=payloads[index],
                    group=group,
                    step=steps[index],
                    after=afters[index],
                )
            )
    return planned


def _components(count: int, dependents: dict[int, list[int]]) -> list[int]:
    """
    Map every testcase to the lowest index of the testcases it is connected to.
    """
    parent = list(range(count))

    def root(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for prerequisite, dependent_indices in dependents.items():
        for dependent in dependent_indices:
            roots = sorted((root(prerequisite), root(dependent)))
            parent[roots[1]] = roots[0]

    return [root(index) for index in range(count)]


def _prerequisites_first(
    indices: list[int],
    afters: list[tuple[str, ...]],
    dependents: dict[int, list[int]],
    origins: list[str],
) -> list[int]:
    """
    Order one group so that every testcase follows all of its prerequisites.
    """
    open_prerequisites = {index: len(afters[index]) for index in indices}
    ready = sorted(index for index in indices if not open_prerequisites[index])
    order: list[int] = []

    while ready:
        index = ready.pop(0)
        order.append(index)
        for dependent in dependents[index]:
            open_prerequisites[dependent] -= 1
            if not open_prerequisites[dependent]:
                ready.append(dependent)
        ready.sort()

    if len(order) != len(indices):
        cyclic = sorted(set(indices) - set(order))
        raise ValueError(
            "ci_after forms a cycle between "
            + ", ".join(origins[index] for index in cyclic)
        )
    return order
