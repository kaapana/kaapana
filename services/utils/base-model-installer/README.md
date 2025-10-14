# README.md

This utility contains an image together with a helm-chart.
Both can be used to download pretrained model weights during the build-process and during a workflow.

The image must be used as baseimage for another image.
The Dockerfile of the final image must contain the following lines

```bash
FROM local-only/base-model-installer:latest

ARG include_model_weights="false"
COPY files/model_lookup.json /model_lookup.json
RUN python3 -u /kaapana/app/provide_models.py --all=$include_model_weights
```

The file `model_lookup.json` must satisfy the following schema:

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.com/task-schema.json",
    "title": "Download Model Weights Schema",
    "description": "Schema for mapping task names to model download metadata.",
    "type": "object",
    "additionalProperties": {
        "type": "object",
        "required": ["models", "check_file", "download_link"],
        "properties": {
            "id": {
            "type": "string",
            "pattern": "^[0-9]{3,}$",
            "description": "A numeric string identifying the task (e.g. '001')."
            },
            "models": {
            "type": "array",
            "minItems": 1,
            "description": "List of model types associated with the task."
            },
            "check_file": {
            "type": "string",
            "description": "Relative path to a file in the model archive that is used to check, if the model is already present."
            },
            "download_link": {
            "type": "string",
            "format": "uri",
            "description": "HTTP or HTTPS URL to download the task dataset zip file."
            },
            "additionalProperties": false
        }
    }
}
```

The helm chart can be added to `requirements.yaml` of another helm chart as
```yaml
- name: model_installer_chart
  version: 0.0.0
```

When the helm chart is installed it expects `.Values.global.task_ids` to be set.
For Kaapana extensions you can add `extension_params` to the `values.yaml` of your helm chart as
```yaml
extension_params:
    task_ids: 
        definition: "Multi-selectable nnunet versions used in different tasks"
        type: "list_multi"
        value: [
        ]
        default: [
        ]

```
When a user installs the extensions in the Extensions View he will be prompted to select a list of task_ids, that should be installed
The items in `extension_params.task_ids.values` and `extension_params.task_ids.default` must match with the object-names in the `model_lookup.json`


## Usage with an operator in a workflow
When you wanna use such an image as processing-container for an Airflow Operator, you have to set the enviroment variable `TASK_IDS` to a comma-separated list of task-ids that match with the objects names in the `model_lookup.json` file in the corresponding container image.