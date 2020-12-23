import os
import sys
import json
import glob
import pathlib
import sched
import time
import datetime
from tensorboardX import SummaryWriter

timeout = 60

args_got = sys.argv[1:]
if (len(args_got) != 3):
    print("Arg0: experiment_path")
    print("Arg1: fold")
    print("Arg2: tensorboard_dir_path")
    print("GOT: ")
    print(args_got)
    print("-> exit")
    exit(1)
else:
    experiment_path = args_got[0]
    fold = args_got[1]
    tensorboard_dir_path = args_got[2]

print("")
print("Starting monitoring....")
print("")
print(f"experiment_path:      {experiment_path}")
print(f"tensorboard_dir_path: {tensorboard_dir_path}")
print(f"fold:                  {fold}")
print("")

s = sched.scheduler(time.time, time.sleep)
writer = None
last_written_epoch = -1
last_training_log_file = None
experiment_name = f"nnunet-train_{datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H_%M')}"

def get_logs(sc):
    global experiment_name, writer, last_written_epoch, experiment_path,fold, tensorboard_dir_path, timeout, last_training_log_file
    logs_path = os.path.join(experiment_path, "**", "training_log_*.txt*")
    log_files = sorted(glob.glob(logs_path, recursive=True))
    logs_path = [i for i in logs_path if f"fold_{fold}" in i]
    # print(f"Checking log files...")
    if len(log_files) > 0:

        if log_files[-1] != last_training_log_file:
            last_training_log_file = log_files[-1]
            debug_json_path = os.path.join(os.path.dirname(last_training_log_file), "debug.json")
            fold_no = int(os.path.basename(os.path.dirname(last_training_log_file)).replace("fold_", ""))
            experiment_log_path = os.path.join(tensorboard_dir_path, experiment_name, f"fold_{fold_no}")
            pathlib.Path(experiment_log_path).parent.mkdir(parents=True, exist_ok=True)

            print("")
            print(f"New log-file found: {last_training_log_file}")
            print(f"Experiment-Log-Path: {experiment_log_path}")
            print(f"Debug.json: {debug_json_path}..")
            print(f"Fold_No: {fold_no}..")
            print("")
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
            writer.add_scalar('loss/train', epoch["train-loss"], epoch["count"])
            writer.add_scalar('loss/validation', epoch["validation-loss"], epoch["count"])

            for i in range(0, len(epoch["foreground-dice"])):
                writer.add_scalar('foreground-dice/label_{}'.format(i), epoch["foreground-dice"][i], epoch["count"])

            writer.add_scalar('time', epoch["time"], epoch["count"])
            last_written_epoch = epoch["count"]
            print("# Tensorboard: Wrote new epoch: {}".format(last_written_epoch))

        writer.flush()

    else:
        print(f"No Logs found at: {logs_path}")

    s.enter(timeout, 1, get_logs, (sc,))


s.enter(60, 1, get_logs, (s,))
s.run()
writer.close()
