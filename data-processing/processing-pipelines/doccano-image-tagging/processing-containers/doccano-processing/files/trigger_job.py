import os
import json
from pathlib import Path

batch_input_dir = os.path.join(
    "/", os.environ["WORKFLOW_DIR"], os.environ["OPERATOR_IN_DIR"]
)

with open(os.path.join(batch_input_dir, "doccanoadmin.json")) as f:
    annotations = json.load(f)

batch_dir = Path("/") / os.environ["WORKFLOW_DIR"] / os.environ["BATCH_NAME"]
batch_dir.mkdir(parents=True, exist_ok=True)

for annotation in annotations:
    for series_instance_uid in annotation["metadata"]["series_instance_uids"]:
        target_dir = batch_dir / series_instance_uid / os.environ["OPERATOR_OUT_DIR"]
        target_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "0020000E SeriesInstanceUID_keyword": series_instance_uid,
            "doccano_tags": annotation["label"],
        }
        with open(target_dir / "metadata.json", "w") as fp:
            json.dump(metadata, fp, indent=4, sort_keys=True)
