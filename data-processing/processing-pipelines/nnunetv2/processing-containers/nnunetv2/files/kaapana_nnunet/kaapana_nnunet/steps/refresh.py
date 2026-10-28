"""Rebuild the form dropdowns from S3 and register raw datasets and pretrained checkpoints uploaded by hand.

A folder nnunet/raw/DatasetXXX_Name/ with a dataset.json and no marker is registered as complete
after its files and dataset.json were checked; the same for nnunet/pretrained/<name>/ with
adaptation_plan.json and checkpoint_final.pth. Leftovers of crashed uploads are removed.
"""

import json
import logging

from kaapana_nnunet import layout, pretrained
from kaapana_nnunet.catalog import sync
from kaapana_nnunet.context import Context, StepError, main, provenance
from kaapana_nnunet.store import IntegrityError

logger = logging.getLogger(__name__)


def run(ctx: Context):
    store = ctx.store
    problems = []
    if ctx.flag("register_uploads", True):
        base = store.key("raw") + "/"
        for obj in store._client().list_objects(store.bucket, prefix=base):
            name = obj.object_name[len(base) :].rstrip("/")
            if not layout.DATASET_RE.match(name) or store.is_published(layout.raw_prefix(name)):
                continue
            keys = {
                o.object_name[len(base) + len(name) + 1 :]
                for o in store._client().list_objects(store.bucket, prefix=f"{base}{name}/", recursive=True)
            }
            if layout.RESERVATION in keys:
                continue  # a create-dataset run is writing it
            if "dataset.json" not in keys:
                problems.append(f"{name}: no dataset.json, not registered")
                continue
            resp = store._client().get_object(store.bucket, f"{base}{name}/dataset.json")
            try:
                dataset_json = json.loads(resp.read())
            except ValueError as e:
                problems.append(f"{name}: dataset.json is not valid JSON ({e})")
                continue
            finally:
                resp.close()
                resp.release_conn()
            missing = {"channel_names", "labels", "numTraining", "file_ending"} - set(dataset_json)
            if missing:
                problems.append(f"{name}: dataset.json lacks {', '.join(sorted(missing))}")
                continue
            try:
                store.adopt(
                    layout.raw_prefix(name), meta=provenance(ctx, dataset=name, cases=dataset_json["numTraining"])
                )
                print(f"Registered uploaded raw dataset {name}", flush=True)
            except IntegrityError as e:
                problems.append(f"{name}: {e}")
        for name in pretrained.uploaded(store):
            files = {
                o.object_name.rsplit("/", 1)[-1]
                for o in store._client().list_objects(store.bucket, prefix=store.key(f"pretrained/{name}") + "/")
            }
            missing = set(pretrained.REQUIRED_FILES) - files
            if missing:
                problems.append(f"pretrained/{name}: {', '.join(sorted(missing))} missing, not registered")
                continue
            try:
                store.adopt(f"pretrained/{name}", meta=provenance(ctx, pretrained=name))
                print(f"Registered uploaded pretrained model {name}", flush=True)
            except IntegrityError as e:
                problems.append(f"pretrained/{name}: {e}")
    store.cleanup_staging()
    sync(ctx)
    print("Dropdowns refreshed.", flush=True)
    if problems:
        raise StepError("Some uploaded folders were not registered:\n" + "\n".join(problems))


if __name__ == "__main__":
    main(run)
