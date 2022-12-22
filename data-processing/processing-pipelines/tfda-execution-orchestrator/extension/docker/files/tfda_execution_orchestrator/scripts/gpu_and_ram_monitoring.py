import subprocess as sp
import os
from threading import Thread , Timer
import sched, time
from datetime import datetime

ram_used = 0
gpu_limit = 11000
ram_limit = 40
medperf_logfile = "/home/ubuntu/medperf-env/logs/medperf.log"

def get_gpu_memory():
    output_to_list = lambda x: x.decode('ascii').split('\n')[:-1]
    ACCEPTABLE_AVAILABLE_MEMORY = 7024
    COMMAND = "nvidia-smi --query-gpu=memory.used --format=csv"
    try:
        memory_use_info = output_to_list(sp.check_output(COMMAND.split(),stderr=sp.STDOUT))[1:]
    except sp.CalledProcessError as e:
        raise RuntimeError("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))
    memory_use_values = [int(x.split()[0]) for i, x in enumerate(memory_use_info)]
    # print(memory_use_values)
    return memory_use_values

def get_ram_usage():
    global ram_used
    # Getting all memory using os.popen()
    total_memory, used_memory, free_memory = map(
    int, os.popen('free -t -m').readlines()[-1].split()[1:])

# Memory usage : since the system uses a default 610 MB always, deducting that to find the actual usage
    ram_used =  (used_memory/1000)-0.61
    #print(ram_used)
    return ram_used


def monitor_gpu_and_ram_usage():
    """
        This function calls itself every sec and prints the GPU and RAM memory consumption. Upon exceeding, it logs the information to medperf.log file and exits.
    """
    Timer(1.0, monitor_gpu_and_ram_usage).start()
    Timer(1.0, get_ram_usage).start()
    print(get_gpu_memory()[0]-1104)
    print(ram_used)
    if get_gpu_memory()[0]-1104 > gpu_limit or ram_used > ram_limit:
        if get_gpu_memory()[0]-1104 > gpu_limit:
            now = datetime.now()
            with open(medperf_logfile, "a") as logfile:
                logfile.write(f"{now.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]} | ERROR: GPU Memory usage exceeded {gpu_limit} GB, value is: {(get_gpu_memory()[0]-1104)/1000} GB")
        elif ram_used > ram_limit:
            now = datetime.now()
            with open(medperf_logfile, "a") as logfile:
                logfile.write(f"{now.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]} | ERROR: RAM usage exceeded {ram_limit} GB, value is: {ram_used} GB")
        
        os._exit(0)
        

monitor_gpu_and_ram_usage()
