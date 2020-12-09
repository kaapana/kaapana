import os
import sys
import json
import glob
import pathlib
import sched
import time
from tensorboardX import SummaryWriter

args_got = sys.argv[1:]
if (len(args_got) != 2):
    print("Arg0: experiment_path")
    print("Arg1: tensorboard_dir_path")
    print("GOT: ")
    print(args_got)
    print("-> exit")
    exit(1)
else:
    experiment_path = args_got[0]
    tensorboard_dir_path = args_got[1]

s = sched.scheduler(time.time, time.sleep)
writer = None
last_written_epoch = -1

def get_logs(sc):
    global writer, last_written_epoch, experiment_path, tensorboard_dir_path
    print("Checking log files...")
    log_files = sorted(glob.glob(os.path.join(experiment_path, "training_log_*.txt*"), recursive=True))
    experiment_name = f'nnunet-train-{log_files[-1].split("training_log_")[-1].replace(".txt","")}'
    experiment_log_path = os.path.join(tensorboard_dir_path, experiment_name)
    pathlib.Path(experiment_log_path).parent.mkdir(parents=True, exist_ok=True)

    if writer is None:
        writer = SummaryWriter(logdir=experiment_log_path)

    epoch_log_data = []
    with open(log_files[-1]) as f:
        content = f.readlines()

    content = [x.strip() for x in content]
    epoch_data = {}
    for line in content:
        if "epoch:" in line:
            epoch_data = {
                "count": int(line.split(":")[-1].strip())
            }
            epoch_log_data.append(epoch_data)
        elif len(epoch_data) == 0:
            continue
        elif "train loss" in line:
            epoch_data["train-loss"] = float(line.split(":")[-1].strip())
        elif "validation loss" in line:
            epoch_data["validation-loss"] = float(line.split(":")[-1].strip())
        elif "Average global foreground Dice" in line:
            epoch_data["foreground-dice"] = [float(x) for x in line.split(":")[-1].strip().replace("[", "").replace("]", "").split(",")]
        elif "lr:" in line:
            epoch_data["lr"] = float(line.split(":")[-1].strip())
        elif "This epoch took" in line:
            epoch_data["time"] = float(line.split("This epoch took")[-1].strip()[:-2])

    for epoch in epoch_log_data:
        if (len(epoch)) != 6 or last_written_epoch >= epoch["count"]:
            continue
        writer.add_scalar('train loss', epoch["train-loss"], epoch["count"])
        writer.add_scalar('validation loss', epoch["validation-loss"], epoch["count"])
        writer.add_scalars('Average global foreground Dice', {'0': epoch["foreground-dice"][0], '1': epoch["foreground-dice"][1]}, epoch["count"])
        writer.add_scalar('lr', epoch["lr"], epoch["count"])
        writer.add_scalar('time', epoch["time"], epoch["count"])
        last_written_epoch = epoch["count"]
        print("Wrote new Epoch: {}".format(last_written_epoch))
    s.enter(10, 1, get_logs, (sc,))


s.enter(1, 1, get_logs, (s,))
s.run()
writer.close()
