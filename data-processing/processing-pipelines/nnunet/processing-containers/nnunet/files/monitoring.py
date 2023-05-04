import os
import sys
import json
import glob
import pathlib
import sched
import time
import datetime
from shutil import copy2
from os.path import join, basename, dirname
from tensorboardX import SummaryWriter

#######################
##### Deprecated! #####
#######################

timeout = 60

args_got = sys.argv[1:]
if len(args_got) != 4:
    print("# Arg0: experiment_path")
    print("# Arg1: fold")
    print("# Arg2: tensorboard_dir_path")
    print("# Arg3: nnUNet_raw_data_base")
    print("# GOT: ")
    print(args_got)
    print("# -> exit")
    exit(1)
else:
    experiment_path = args_got[0]
    fold = args_got[1]
    tensorboard_dir_path = args_got[2]
    nnUNet_raw_data_base = args_got[3]


print("# ")
print("# Starting monitoring....")
print("# ")
print(f"# experiment_path:      {experiment_path}")
print(f"# tensorboard_dir_path: {tensorboard_dir_path}")
print(f"# nnUNet_raw_data_base: {nnUNet_raw_data_base}")
print(f"# fold:                 {fold}")
print("# ")

s = sched.scheduler(time.time, time.sleep)
writer = None
last_written_epoch = -1
last_training_log_file = None
experiment_name = f"nnunet-train_{datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H_%M')}"

dataset_json_path = join(nnUNet_raw_data_base, "nnUNet_raw_data", "**", "dataset.json")
dataset_json_path = glob.glob(dataset_json_path, recursive=True)
if len(dataset_json_path) == 1:
    dataset_json_path = dataset_json_path[0]
    with open(dataset_json_path) as json_file:
        dataset_json = json.load(json_file)
    dataset_json.pop("test", None)
    dataset_json.pop("training", None)

else:
    print("#")
    print("#")
    print("# Could not find dataset.json!")
    print("#")
    print("#")
    dataset_json = None


def get_logs(sc):
    global experiment_name, writer, last_written_epoch, experiment_path, fold, tensorboard_dir_path, timeout, last_training_log_file, dataset_json
    logs_path = join(experiment_path, "**", "training_log_*.txt*")
    log_files = sorted(glob.glob(logs_path, recursive=True))
    log_files = [i for i in log_files if "fold" not in i or f"fold_{fold}" in i]
    if len(log_files) > 0:
        if log_files[-1] != last_training_log_file:
            last_training_log_file = log_files[-1]
            if dataset_json != None:
                with open(
                    join(dirname(last_training_log_file), "dataset.json"), "w"
                ) as outfile:
                    json.dump(dataset_json, outfile, indent=4, sort_keys=False)

            # debug_json_path = join(dirname(last_training_log_file), "debug.json")
            if "fold" in last_training_log_file:
                fold_no = int(
                    basename(dirname(last_training_log_file)).replace("fold_", "")
                )
                experiment_log_path = join(
                    tensorboard_dir_path, experiment_name, f"fold_{fold_no}"
                )
                print(f"# Fold_No: {fold_no}..")
            else:
                experiment_log_path = join(tensorboard_dir_path, experiment_name)

            pathlib.Path(experiment_log_path).parent.mkdir(parents=True, exist_ok=True)

            print("# ")
            print(f"# New log-file found: {last_training_log_file}")
            print("# ")
            writer = SummaryWriter(logdir=experiment_log_path)

            # with open(debug_json_path) as json_file:
            #     debug_info = json.load(json_file)

            # writer.add_text('Text', 'text logged at step:' + str(n_iter), n_iter)

        epoch_log_data = []
        with open(last_training_log_file) as f:
            content = f.readlines()

        content = [x.strip() for x in content]
        epoch_data = {}
        for line in content:
            if "epoch:" in line:
                epoch_data = {"count": int(line.split(":")[-1].strip())}
                epoch_log_data.append(epoch_data)
            elif len(epoch_data) == 0:
                continue
            elif "train loss" in line:
                epoch_data["train-loss"] = float(line.split(":")[-1].strip())
            elif "validation loss" in line:
                epoch_data["validation-loss"] = float(line.split(":")[-1].strip())
            elif "Average global foreground Dice" in line:
                epoch_data["foreground-dice"] = [
                    float(x)
                    for x in line.split(":")[-1]
                    .strip()
                    .replace("[", "")
                    .replace("]", "")
                    .split(",")
                ]
            elif "lr:" in line:
                epoch_data["lr"] = float(line.split(":")[-1].strip())
            elif "This epoch took" in line:
                epoch_data["time"] = float(
                    line.split("This epoch took")[-1].strip()[:-2]
                )

        for epoch in epoch_log_data:
            if (len(epoch)) != 6 or last_written_epoch >= epoch["count"]:
                continue
            writer.add_scalar("loss/train", epoch["train-loss"], epoch["count"])
            writer.add_scalar(
                "loss/validation", epoch["validation-loss"], epoch["count"]
            )

            scalars_dict = {}
            for i in range(0, len(epoch["foreground-dice"])):
                label_tag = str(i + 1)
                if dataset_json != None and label_tag in dataset_json["labels"]:
                    label_tag = dataset_json["labels"][label_tag]
                scalars_dict[label_tag] = epoch["foreground-dice"][i]
                writer.add_scalar(
                    f"foreground-dice/label_{label_tag}",
                    epoch["foreground-dice"][i],
                    epoch["count"],
                )

            # writer.add_scalars("foreground-dice/combined",scalars_dict,epoch["count"])
            writer.add_scalar("time", epoch["time"], epoch["count"])
            last_written_epoch = epoch["count"]
            print(f"# Tensorboard: Wrote new epoch: {last_written_epoch}")

        writer.flush()

    else:
        print(f"# No Logs found at: {logs_path}")

    s.enter(timeout, 1, get_logs, (sc,))


s.enter(60, 1, get_logs, (s,))
s.run()
writer.close()
