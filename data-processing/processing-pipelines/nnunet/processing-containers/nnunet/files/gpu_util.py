import os
from pynvml import *


def bytesto(bytes, to, bsize=1024):
    a = {"k": 1, "m": 2, "g": 3, "t": 4, "p": 5, "e": 6}
    r = float(bytes)
    return bytes / (bsize ** a[to])


gpu_mem_needed = os.getenv("GPU_MEM_NEEDED", None)
print("# ")
print("# Starting GPU util-check...")
print("# ")
print(f"# GPU_MEM_NEEDED: {gpu_mem_needed}")

visible_device = None
if gpu_mem_needed != None:
    try:
        nvmlInit()
        gpu_mem_needed = int(gpu_mem_needed)
        deviceCount = nvmlDeviceGetCount()
        driver_version = nvmlSystemGetDriverVersion()
        print(f"# deviceCount:    {deviceCount}")
        print(f"# Driver_Version: {driver_version}")
        for i in range(deviceCount):
            print("# ")
            print(f"# Checking GPU: {i}")
            print("# ")
            handle = nvmlDeviceGetHandleByIndex(i)
            gpu_name = nvmlDeviceGetName(handle)
            info = nvmlDeviceGetMemoryInfo(handle)
            free = bytesto(info.free, "m")
            used = bytesto(info.used, "m")
            total = bytesto(info.total, "m")
            print(f"# GPU: {gpu_name}")
            print(f"# total: {total}")
            print(f"# free:  {free}")
            print(f"# used:  {used}")
            if gpu_mem_needed < free:
                print(f"# GPU {i} has enough free memory!")
                visible_device = i
                break
            else:
                print(f"# GPU {i} has not enough free memory!")
            print("# ")

    except Exception as e:
        print("# Issue with util-check!")
        print(e)
        print("# Abort ")

    finally:
        nvmlShutdown()
else:
    print("# No GPU_MEM specified! -> return")

print(f"# RETURNING: {visible_device}")
print(f"{visible_device}")
