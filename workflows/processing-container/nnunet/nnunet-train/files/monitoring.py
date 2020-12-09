import os
import json
import glob

#training_log_2020_12_8_17_17_05
log_dir_path="/home/jonas/nnunet_logs"
log_files = sorted(glob.glob(os.path.join(log_dir_path, "*.txt*"), recursive=True))

with open(log_files[-1]) as f:
    content = f.readlines()
 
content = [x.strip() for x in content] 
for line in content:
    if "epoch:" in line:
        print("New Epoch data!")
    print(f"Line: {line}")
