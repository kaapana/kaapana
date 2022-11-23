import socket
import time
import os
import requests


def check_url(url):
    print("")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("Checking URL: {}".format(url))
    try:
        request = requests.get(url, timeout=2,  allow_redirects=False, verify=False)
        print("STATUS CODE: {}".format(request.status_code))
        if request.status_code == 200:
            print('{}: OK'.format(url))
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("")
            return 0
        else:
            print("NOT FOUND - Wait for URL: {}".format(url))
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("")
            return 1
    except Exception as e:
        print("NOT FOUND - Wait for URL: {}".format(url))
        print("Error: {}".format(e))
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("")
        return 1


# os.environ['WAIT'] = 'airlfow,116.203.203.19,80,/flow/kaapana/api/getdagss'
# os.environ['DELAY'] = '1'


def check_port(name, host, port, delay):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        while sock.connect_ex((host, int(port))) != 0:
            print("Wait for Service: %s  on host: %s and port: %s!" % (name, host, port))
            time.sleep(delay)
        print("Service: %s  is READY!!!! host: %s and port: %s!" % (name, host, port))
        return 0

    except Exception as e:
        # print(e)
        print("Service: %s  host: %s is not known! Try again..." % (name, host))
        return 1


wait_env = os.getenv('WAIT', None)
wait_env = wait_env if wait_env != "" else None

delay = os.getenv('DELAY', None)
delay = delay if delay != "" else None

files_and_folders_exists = os.getenv('FILES_AND_FOLDERS_EXISTS', None)
files_and_folders_exists = files_and_folders_exists if files_and_folders_exists != "" else None

print("Start service-checker ...")
print("")
print("")
print(f"{wait_env=}")
print(f"{delay=}")
print(f"{files_and_folders_exists=}")
print("")

if delay != None:
    delay = int(delay)


if (wait_env == None and files_and_folders_exists == None) or delay == None:
    print("WAIT, FILES_AND_FOLDERS_EXISTS or DELAY == None! Usage: WAIT='postgres,localhost,5432;...' + DELAY= int delay in sec + FILES_AND_FOLDERS_EXISTS='/home/charts/file.json'")
    exit(0)

if files_and_folders_exists != None and delay != None:
    
    if files_and_folders_exists.endswith(';'):
        files_and_folders_exists = files_and_folders_exists[:-1]
    
    for file_or_folder in files_and_folders_exists.split(";"):
        while not os.path.exists(file_or_folder):
            time.sleep(delay)
            print(f'Checking for {file_or_folder}')

if wait_env != None and delay != None:
    if wait_env[len(wait_env)-1] == ";":
        wait_env = wait_env[:len(wait_env)-1]

    commands = wait_env.split(";")
    for cmd in commands:
        name = cmd.split(",")[0]
        host = cmd.split(",")[1]
        port = cmd.split(",")[2]
        if len(cmd.split(",")) == 4:
            url = cmd.split(",")[3]
            if port == "443":
                scheme = "https://"
            else:
                scheme = "http://"
            url = "{}{}:{}{}".format(scheme, host, port, url)
            while check_url(url) != 0:
                time.sleep(delay)
        else:
            while check_port(name, host, port, delay) != 0:
                # print("Service not known... try again")
                time.sleep(delay)