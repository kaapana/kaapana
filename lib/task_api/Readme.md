# Readme

## Motivation
The main reason of the Task API should be a contract about how to develop processing-containers that can be run inside a Workflow in Kaapana. This contract exist of two parts.
1. A processing-container is required to contain standardized information about how to use it. We call a file that satisfies the standard `processing-contaner.json`. The contract defines the schema of this file and how it must be attached to the container.
2. There is a standardized API that enables developers to run a processing-container by providing a Task object. This API comes in form of a python library.


## The processing-container.json
The processing-container.json file includes sufficient information, such that a user only has to provide paths to the input data in order to run the processing-container.


## The task API
The task API must contain following functionalities
* Get the processing-container.json file from a valid processing-container.
* Validate Task objects.
* Merge Task objects with the processing-container.json.
* Start a container based on a Task object
* Receive logs from a container

## The python library
### Install
```bash
python3 -m build
python3 -m pip install dist/task_api-0.1.0.tar.gz
```

### Get a processing-container json file
```bash
python3 -m task_api.cli processing-container <image> --mode docker 
```

### Run a task in docker
```bash
python3 -m task_api.cli run <path-to-task.json> --mode docker
```

### Testing
```bash
coverage run -m pytest 
coverage report -m
```

### pydantic models
```bash
python3 -m pip install datamodel-codegen
cd task_api/processing-container
datamodel-codegen --input schemas/ --input-file-type jsonschema --output generated-models/ --target-python-version 3.12 --output-model-type pydantic_v2.BaseModel --use-annotate
```

## Monitoring functionality
You can monitor the memory peak of the container started with `task_api.cli.py run` with the flag `--monitor-container`. This works only locally with Docker. If the `taks.json` file includes scaleRules, our tool will also check, if the computed Resource specification matches with the memory usage.

The following section documents the decision for the chosen implementation of monitoring peak memory usage of a container:

| Approach| Description | Accuracy | Portability | Pros | Cons |
| ---- | --- | ----- | --- | --- | --- |
| **`/proc/<pid>/status` (e.g., `VmPeak`)** | Reads memory info of container's main process   | ❌ Not container-aware (may include shared memory, overhead) | Linux-only | Easy to access per-process stats | Not accurate for total container usage, includes host OS memory accounting |
| **`docker stats` (or Docker SDK)** | Uses Docker's built-in metrics, shows live usage  | ✅ Container-aware | Docker-specific | No need to access cgroup paths manually  | No direct peak memory tracking, live-only |
| **Python `tracemalloc`**  | Tracks memory allocation inside Python code | ❌ Application-level only | Python-specific | Great for debugging Python memory leaks  | Doesn't reflect total memory used by the container or native extensions |
| **`/sys/fs/cgroup/<container-specific-path>/memory.current`** | Shows live memory usage from the cgroup | ✅ Accurate | Cgroup v2 required | Reflects true kernel view of container memory | No historical (peak) info |
| **`/sys/fs/cgroup/<container-specific-path>/memory.peak`** | Shows **peak memory usage** of the container since startup | ✅ Accurate and authoritative | Cgroup v2 required | Reliable, kernel-enforced metric | Only available on cgroup v2, path can vary with runtime |

We chose to monitor container memory usage via the file: 
```bash
/sys/fs/cgroup/<container-specific-path>/memory.peak
```
The container specific path can be determined from the file `/proc/{pid}/cgroup`.

Reasoning:
* It provides an authoritative and kernel-tracked value for peak memory usage
* It is independent of programming language or container image internals
* It is more accurate and reliable than alternatives like VmPeak from /proc/<pid>/status, which can include memory not strictly attributed to the container (e.g., page cache, shared libs)
* It works from the host and requires no intrusive tooling inside the container


## Connecting Airflow to the task API

Possible solutions:
* Custom KaapanaTaskOperator
* KubernetesPodOperator
* Custom KaapanaExecutor
* KubernetesExecutor

Requirements:
* The solution HAS TO be able to understand information corresponding to a Task object
* The solution HAS TO be able to execute a Container within a Kubernetes cluster based on the information required to create a Task object
* The solution HAS TO be able to forward user input to the Rest API to dedicated tasks
* The solution MUST support to link output channels of upstream tasks to input channel of downstream tasks
* The solution HAS TO allow users to restart tasks
* The solution HAS TO clean output destinations before running a task
* The solution HAS TO provide container logs to the task

* The solution IS ALLOWED to utilize the KubernetesRunner from the task_api library
* The solution SHOULD only execute a task, if there are sufficient resources available in the cluster