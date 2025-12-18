from task_api.processing_container.pc_models import ProcessingContainer
from task_api.processing_container.task_models import Task
import json

processing_container_schema = ProcessingContainer.model_json_schema()
with open("ProcessingContainer.schema.json", "w") as f:
    json.dump(processing_container_schema, f, indent=2)

task_schema = Task.model_json_schema()
with open("Task.schema.json", "w") as f:
    json.dump(task_schema, f, indent=2)
