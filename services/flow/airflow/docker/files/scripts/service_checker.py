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


wait_env = os.getenv('WAIT', "None")
delay = os.getenv('DELAY', "None")
if delay != "None":
    delay = int(delay)

if wait_env != "None" and delay != "None":
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
else:
    print("WAIT or DELAY == None! Usage: WAIT='postgres,localhost,5432;...' + DELAY= int delay in sec")
    exit(1)
