

TASK_IDS is a comma-separated list of task_ids

The image requires a file the file `/model_lookup.json` to be present in the image.
This file must satisfy the following json schema.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/task-schema.json",
  "title": "Task Configuration Schema",
  "description": "Schema for mapping task names to model download metadata.",
  "type": "object",
  "patternProperties": {
    "^Task[0-9]{3,}_.+$": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "pattern": "^[0-9]{3,}$",
          "description": "A numeric string identifying the task (e.g. '001')."
        },
        "models": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": ["2d", "3d_fullres"]
          },
          "minItems": 1,
          "description": "List of model types associated with the task."
        },
        "check_file": {
          "type": "string",
          "description": "Name of a file or a key string used for validation."
        },
        "download_link": {
          "type": "string",
          "format": "uri",
          "description": "HTTP or HTTPS URL to download the task dataset zip file."
        }
      },
      "required": ["id", "models", "check_file", "download_link"],
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}

```