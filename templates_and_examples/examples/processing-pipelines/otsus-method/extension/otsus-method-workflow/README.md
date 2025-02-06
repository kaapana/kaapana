# otsus-method-workflow

An example workflow extension for Kaapana. Uses [Otsu's method](https://en.wikipedia.org/wiki/Otsu%27s_method) to perform automatic thresholding to input images.

* Input: dicom image
* Output:
    * generates a `dcmseg` object in the PACS
    * generates a notebook pdf and a html inside Minio under `<project-name>/staticwebsiteresults/generate-otsus-report/otsus_report_otsus-method-<uid>.<html/pdf>`. Html file is also visible under `Workflow Results` section of the UI


![otsus-method-workflow](https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/img/otsus-method-workflow.png "otsus-method-workflow")

Custom operators:
* `otsus-method` (class: `OtsusMethodOperator`)
* `generate-otsus-report` (class: `OtsusNotebookOperator`)

## About the folder structure of Kaapana Workflow Extensions:

### `extension/docker`
This is where the Airflow DAG and operator definition files are stored as python files. The Dockerfile should build an image containing all these files, dags must be copied to `/kaapana/tmp/dags/` custom operators to `/kaapana/tmp/dags/<workflow-name>/`. These will be copied to Airflow runtime environment inside the Kaapana instance.

#### `extension/docker/files/dag_<name>.py`**
Airflow DAG (Directed Acyclic Graph) definition file. This defines how operators are linked inside the DAG and which parameters are passed from the worfklow UI inside `ui_forms.workflow_form`

#### `extension/docker/files/<folder>/<name>Operator.py`**
Custom operators defitions that are used inside the DAG. You can use [the existing operators provided in Kaapana](https://kaapana.readthedocs.io/en/stable/development_guide/operators.html) directly by importing them in your DAG definition file.

### `extension/<name>-workflow`
This directory contains the Helm chart of the workflow. There should be a `dependencies` field in either a separate `requirements.yaml` file (works with all Helm versions) or inside `Chart.yaml` (works with Helm v3 and later). Kaapana Workflow Extensions require `dag-installer-chart`, which is used for copying the DAG and operator definition files inside Airflow runtime of Kaapana. As an optional parameter, a `repository` field with the relative path to the dag-installer-chart can be specified to enable running `helm dep up` when packaging the Helm Chart on its own (i.e. without running the build script).

### `extension/<name>-workflow/values.yaml`
This file can be used to pass parameters inside the Helm chart. Two default parameters that are passed to `dag-installer-chart` are:
* `global.image`: this specifies the image name that contains DAG and operator definitions
* `global.action`: one of "copy", "remove" or "prefetch"

### `processing-containers/*`
This folder contains the container images that are pulled by the custom operators of this workflow extension. They are usually in the format of `processing-containers/*/Dockerfile` and `processing-containers/*/files/*`. It is only necessary that a Dockerfile exists under this path and that the image can be built via docker, podman or other OCI compliant container engines.

#### `processing-containers/*/Dockerfile`
Dockerfiles should include

```
FROM <base-image> 

LABEL IMAGE="<image-name>" # image name as str 
LABEL VERSION="<image-version>" # image version str 
LABEL BUILD_IGNORE="<is-ignored>" # either True or False, the build script skips building the image if True
LABEL REGISTRY="local-only" # OPTIONAL. If "local-only", build script skips pushing the image. If empty, the registry-url passed from build.yaml is used
```

so that the tag of the image is constructed as `<registry-url>/<image-name>:<image-version>`
