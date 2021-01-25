import os
import json
import sys


args_got = sys.argv[1:]
if (len(args_got) != 1):
    print("Arg0: target_path")
    print("GOT: ")
    print(args_got)
    print("-> exit")
    exit(1)
else:
    print(f"RESULT_DIR: {args_got[0]}")

task_name = os.getenv("TASK", "N/A")
model_architecture = os.getenv("TRAIN_NETWORK", "UNKNOWN")  # -> model 2d,3d_lowres etc
network_trainer = os.getenv("TRAIN_NETWORK_TRAINER", "N/A")
training_description = os.getenv("TRAINING_DESCRIPTION", "N/A")

target_organs = os.getenv("SEG_FILTER", "N/A").split(",")
shuffle_seed = int(os.getenv("SHUFFLE_SEED", "0"))
test_percentage = int(os.getenv("TEST_PERCENTAGE", "0"))
input_modality = os.getenv("INPUT", "N/A")
prep_modalities = os.getenv("PREP_MODALITIES", "N/A").split(",")

model_dir = os.path.join(args_got[0], "nnUNet", model_architecture, task_name)
model_info_path = os.path.join(model_dir, "model_info.json")

if not os.path.exists(model_dir):
    os.makedirs(model_dir, exist_ok=True)

print("# ")
print("# Starting wite-model-info...")
print("# ")
print(f"# path: {model_info_path}")
print("# ")

model_info = {
    "description": training_description,
    "model": [model_architecture],
    "input-mode": "all",
    "input": prep_modalities,
    "body_part": "N/A",
    "targets": target_organs,
    "supported": True,
    "info": "N/A",
    "url": "N/A",
    "task_url": "N/A",
    "task_name": task_name,
    "network_trainer": network_trainer,
    "shuffle_seed": shuffle_seed,
    "test_percentage": test_percentage,
    "input_modality": input_modality
}

print("# model_info:")
print(json.dumps(model_info, indent=4, sort_keys=True))
print("# ")
with open(model_info_path, 'w') as outfile:
    json.dump(model_info, outfile, indent=4, sort_keys=True)

print("# ")
print("# DONE")
print("# ")
