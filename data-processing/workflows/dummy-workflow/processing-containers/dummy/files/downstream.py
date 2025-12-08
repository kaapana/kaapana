from pathlib import Path
import time
import os

TIME_SLEEP = os.getenv("TIME_SLEEP", 10)

CHANNEL1 = Path("/home/downstream/channel1")
CHANNEL2 = Path("/home/downstream/channel2")


for channel in [CHANNEL1, CHANNEL2]:
    print(f"Read files from input channel {channel}")
    for file in channel.iterdir():
        if file.is_file():
            print(f"Read file {file}")
            with open(file, "r") as f:
                for line in f.readlines():
                    print(line)

for i in range(int(TIME_SLEEP)):
    time.sleep(1)
    print(i)
