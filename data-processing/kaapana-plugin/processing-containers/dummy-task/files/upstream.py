from pathlib import Path
import time
import os

TIME_SLEEP = os.getenv("TIME_SLEEP", 10)

CHANNEL1 = Path("/home/dummy/channel1")
CHANNEL2 = Path("/home/dummy/channel2")


msg = "Hello channel 1!"
print(msg)
with open(CHANNEL1 / "dummy.txt", "w") as f:
    f.write(msg)

msg = "Hello channel 2!"
print(msg)
with open(CHANNEL2 / "dummy.txt", "w") as f:
    f.write(msg)


for i in range(int(TIME_SLEEP)):
    time.sleep(1)
    print(i)
