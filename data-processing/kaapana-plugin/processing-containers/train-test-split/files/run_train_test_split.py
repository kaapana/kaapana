import sys, os
import glob
import json
import random
from pathlib import Path

train_tag = os.getenv("TRAIN_TAG", "train")
test_tag = os.getenv("TEST_TAG", "test")
random_seed = int(os.getenv("RANDOM_SEED", 1))
split = float(os.getenv("SPLIT", 0.8))


def add_tag(batch_element_dir, tag):
    json_files = sorted(
        glob.glob(
            os.path.join(batch_element_dir, os.environ["OPERATOR_IN_DIR"], "*.json*"),
            recursive=True,
        )
    )
    for meta_files in json_files:
        print(f"Do tagging for file {meta_files}")
        with open(meta_files) as fs:
            metadata = json.load(fs)
        metadata["train_test_split_tag"] = [tag]
        target_dir = Path(batch_element_dir) / os.environ["OPERATOR_OUT_DIR"]
        target_dir.mkdir(parents=True, exist_ok=True)
        with open(target_dir / "metadata.json", "w") as fp:
            json.dump(metadata, fp, indent=4, sort_keys=True)


print(
    f"Using train_tag: {train_tag}, test_tag: {test_tag}, split: {split} and random_seed: {random_seed}"
)

batch_folders = sorted(
    [
        f
        for f in glob.glob(
            os.path.join("/", os.environ["WORKFLOW_DIR"], os.environ["BATCH_NAME"], "*")
        )
    ]
)


if split > 1:
    train_split = int(split)
else:
    train_split = round(split * len(batch_folders))

if train_split > len(batch_folders):
    raise ValueError("Train split is bigger than the number of selected samples!")

random.seed(random_seed)
random.shuffle(batch_folders)
for batch_element_dir in batch_folders[:train_split]:
    add_tag(batch_element_dir, train_tag)

for batch_element_dir in batch_folders[train_split:]:
    add_tag(batch_element_dir, test_tag)
