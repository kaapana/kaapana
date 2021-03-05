import os
import sys
import glob
import json
import pathlib
from os.path import join, basename, dirname, exists
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from datetime import datetime


def create_json_report(log_files, target_path):
    for log_file in log_files:
        print(f"# Processing log-file: {log_file}..")
        dataset_json = None
        dataset_json_path = join(dirname(log_file), "dataset.json")
        if exists(dataset_json_path):
            with open(dataset_json_path) as json_file:
                dataset_json = json.load(json_file)

        fold_data = {}
        if "fold" in log_file:
            fold = basename(dirname(log_file)).replace("fold_", "")
        else:
            fold = basename(dirname(log_file))

        print(f"# fold: {fold}..")
        fold_data = {"fold": fold}
        
        if dataset_json != None:
            fold_data["name"]=dataset_json["name"] if "name" in dataset_json else "N/A"
            fold_data["description"]=dataset_json["description"] if "description" in dataset_json else "N/A"
            fold_data["labels"]=dataset_json["labels"] if "labels" in dataset_json else "N/A"
            fold_data["licence"]=dataset_json["licence"] if "licence" in dataset_json else "N/A"
            fold_data["modality"]=dataset_json["modality"] if "modality" in dataset_json else "N/A"
            fold_data["network_trainer"]=dataset_json["network_trainer"] if "network_trainer" in dataset_json else "N/A"
            fold_data["numTest"]=dataset_json["numTest"] if "numTest" in dataset_json else "N/A"
            fold_data["numTraining"]=dataset_json["numTraining"] if "numTraining" in dataset_json else "N/A"
            fold_data["reference"]=dataset_json["reference"] if "reference" in dataset_json else "N/A"
            fold_data["release"]=dataset_json["release"] if "release" in dataset_json else "N/A"
            fold_data["shuffle_seed"]=dataset_json["shuffle_seed"] if "shuffle_seed" in dataset_json else "N/A"
            fold_data["tensorImageSize"]=dataset_json["tensorImageSize"] if "tensorImageSize" in dataset_json else "N/A"

        fold_data["epochs"] = []
        with open(log_file) as f:
            content = f.readlines()

        content = [x.strip() for x in content]
        epoch_data = {}
        for line in content:
            if "epoch:" in line:
                epoch_data = {
                    "no": int(line.split(":")[-1].strip()),
                }

            elif len(epoch_data) == 0:
                if "lr:" in line:
                    line = line.split(": lr:")
                    fold_data["starting_timestamp"] = line[0]
                    fold_data["initial_lr"] = line[-1]
                continue
            elif "train loss" in line:
                epoch_data["train-loss"] = float(line.split(":")[-1].strip())
            elif "validation loss" in line:
                epoch_data["validation-loss"] = float(
                    line.split(":")[-1].strip())
            elif "Average global foreground Dice" in line:
                dices = [float(x) for x in line.split(":")[-1].strip().replace("[", "").replace("]", "").split(",")]
                if dataset_json != None and len(dataset_json["labels"])-1 == len(dices):
                    labels_dict = {}
                    for i in range(0, len(dices)):
                        labels_dict[dataset_json["labels"][str(i+1)]] = dices[i]

                    epoch_data["foreground-dice"] = labels_dict
                else:
                    epoch_data["foreground-dice"] = dices

            elif "lr:" in line:
                epoch_data["lr"] = float(line.split(":")[-1].strip())
            elif "This epoch took" in line:
                epoch_data["time"] = float(line.split("This epoch took")[-1].strip()[:-2])
                fold_data["epochs"].append(epoch_data)

        report_json_path = join(log_file.replace(".txt", ".json"))
        with open(report_json_path, 'w', encoding='utf-8') as f:
            json.dump(fold_data, f, indent=4, sort_keys=False)

    report_json_path = join(target_path, ("training_log.json"))
    with open(report_json_path, 'w', encoding='utf-8') as f:
        json.dump(fold_data, f, indent=4, sort_keys=False)



# START
args_got = sys.argv[1:]
if (len(args_got) != 2):
    print("# Arg0: experiment_path")
    print("# Arg1: target_path")
    print("# GOT: ")
    print(args_got)
    print("# -> exit")
    exit(1)
else:
    experiment_path = args_got[0]
    target_path = args_got[1]

print("# ")
print("# Starting export report...")
print("# ")
print(f"# experiment_path: {experiment_path}")
print(f"# target_path: {target_path}")
print("# ")

pathlib.Path(target_path).mkdir(parents=True, exist_ok=True)
progress_images_list = sorted(glob.glob(join(experiment_path, "**", "progress.png"), recursive=True))
log_files = sorted(glob.glob(join(experiment_path, "**", "training_log_*.txt*"), recursive=True))
create_json_report(log_files=log_files, target_path=target_path)


timestamp = datetime.now().strftime("%d_%m_%Y")
print(f"# 'progress.png'-list: {progress_images_list} ")
print(f"# Timestamp: {timestamp}")

# font = ImageFont.truetype("sans-serif.ttf", 16)
# img = Image.new('RGB', (0, 400), color = 'white')

im_list = []
for image_path in progress_images_list:
    img_filename = basename(image_path)
    rgba = Image.open(image_path)
    rgb = Image.new('RGB', rgba.size, (255, 255, 255))  # white background
    rgb.paste(rgba, mask=rgba.split()[3])
    draw = ImageDraw.Draw(rgb)
    draw.text((0, 0), f"Report: {img_filename}", (0, 0, 0))  # ,font=font)
    im_list.append(rgb)

pdf1_filename = join(target_path, f'nnunet_report_{timestamp}.pdf')

print(f"# Save report pdf at: {pdf1_filename}")
im_list[0].save(pdf1_filename, "PDF", resolution=100.0,
                save_all=True, append_images=im_list[1:])


print("# saved report.")
