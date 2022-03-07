from subprocess import PIPE, run
import json

log_list = []


def make_log(std_out, std_err):
    std_out = std_out.split("\n")[-100:]
    log = {}
    len_std = len(std_out)
    for i in range(0, len_std):
        log[i] = std_out[i]

    std_err = std_err.split("\n")
    for err in std_err:
        if err != "":
            len_std += 1
            log[len_std] = "ERROR: {}".format(err)

    return log


def execute_helm_command(command):
    print("executing: {}".format(command))
    command = [command]
    output = run(command, stdout=PIPE, stderr=PIPE,
                 universal_newlines=True, timeout=10)
    log = make_log(std_out=output.stdout, std_err=output.stderr)

    if output.returncode != 0 or "The Kubernetes package manager" in output.stdout:
        print("Helm command failed")

    else:
        print("Helm command success")

    print(json.dumps(log, indent=4, sort_keys=True))


command=["helm","install",""]
execute_helm_command("helm")
