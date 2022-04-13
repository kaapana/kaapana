#!/usr/bin/python3.6

import json
import shutil
import os
from time import time
import ansible.parsing.yaml.objects as ans_objects
from ansible.module_utils.common.collections import ImmutableDict
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
from ansible import context
import ansible.constants as C


def timestamp():
    return str(int(time() * 1000))


def handle_loop_results(loop_results, task_name, host_name, loglevel):
    for loop_res in loop_results:
        loop_id = list(filter(None, loop_res["item"].split(" ")))

        if len(loop_id) == 1:
            loop_id = loop_id[0]
        else:
            loop_id = loop_id[1]

        loop_log = {
            "cmd": loop_res["cmd"] if 'cmd' in loop_res else "",
            "msg": loop_res["msg"] if 'msg' in loop_res else "",
            "rc": loop_res["rc"] if 'rc' in loop_res else "",
            "std_out": loop_res["stdout_lines"] if 'stdout_lines' in loop_res and loop_res["stdout_lines"] != [] else "",
            "std_err": loop_res["stderr_lines"] if 'stderr_lines' in loop_res and loop_res["stderr_lines"] != [] else "",
        }
        loop_entry = {
            "suite": global_testsuite if not global_nested_testsuite else host_name,
            "test": global_testname,
            "step": "{}: {}".format(task_name, loop_id),
            "log": loop_log if loop_log["std_out"] != "" or loop_log["std_err"] != "" else "",
            "loglevel": loglevel,
            "timestamp": timestamp(),
            "message": "Task successful.",  # result._result['msg'] if "msg" in result._result else "Task successful.",
            "rel_file": global_playbook_path,
        }
        global_log_list.append(loop_entry)


class ResultCallback(CallbackBase):
    global global_return_value, global_playbook_path, global_log_list, global_testsuite, global_testname, global_nested_testsuite

    def finish_test(self, host_name):
        entry = {
            "suite": global_testsuite if not global_nested_testsuite else host_name,
            "test": global_testname,
            "timestamp": timestamp(),
            "test_done": True,
        }
        global_log_list.append(entry)
        # print(json.dumps(global_log_list,indent=4,sort_keys=True))

    def __init__(self, *args, **kwargs):
        super(ResultCallback, self).__init__(*args, **kwargs)

    def v2_playbook_on_play_start(self, play, *args, **kwargs):
        pass

    def v2_playbook_on_task_start(self, task, is_conditional, *args, **kwargs):
        pass

    def v2_runner_on_unreachable(self, result, ignore_errors=False):
        global global_return_value
        host_name = result._host.get_name()
        task = result._task.get_name()
        changed = result._result['changed']

        print("{0: <15} - HOST UNREACHABLE: {1}".format(host_name, task))

        entry = {
            "suite": global_testsuite if not global_nested_testsuite else host_name,
            "test": global_testname,
            "step": task,
            "log": "",
            "loglevel": "ERROR",
            "timestamp": timestamp(),
            "message": "Host unreachable.",
            "rel_file": global_playbook_path,
        }
        global_log_list.append(entry)
        global_return_value[host_name] = "FAILED"

        self.finish_test(host_name=host_name)

    def v2_runner_on_ok(self, result,  *args, **kwargs):
        global global_return_value
        host_name = result._host.get_name()
        task = result._task.get_name()
        changed = result._result['changed'] if "changed" in result._result else False

        if "loop:" in task.lower() and "results" in result._result:
            task = task.lower().replace("loop: ", "")
            handle_loop_results(loop_results=result._result["results"], task_name=task, loglevel="info", host_name=host_name)

        log = {
            "cmd": result._result["cmd"] if 'cmd' in result._result else "",
            "msg": result._result["msg"] if 'msg' in result._result else "",
            "rc": result._result["rc"] if 'rc' in result._result else "",
            "std_out": result._result["stdout_lines"] if 'stdout_lines' in result._result and result._result["stdout_lines"] != [] else "",
            "std_err": result._result["stderr_lines"] if 'stderr_lines' in result._result and result._result["stderr_lines"] != [] else "",
        }

        print("{0: <15} - OK: {1}".format(host_name, task))
        # if changed:
        #     print("{0: <15} - OK:      {}".format(host_name, task))
        # else:
        #     print("{0: <15} - SKIPPED: {}".format(host_name, task))

        if "RESULT".lower() == task.lower():
            result_msg = result._result['msg']
            print("##################################################################################################################")
            print("")
            print("{0: <15} - RESULT MESSAGE: {1}".format(host_name, result_msg))

        elif "RETURN".lower() == task.lower():
            global_return_value[host_name] = result._result['msg']
            result_msg = "RETURN VALUE: {}".format(global_return_value)
            print("RETURN VALUE: {}".format(global_return_value))
            print("")

        entry = {
            "suite": global_testsuite if not global_nested_testsuite else host_name,
            "test": global_testname,
            "step": task,
            "log": log if log["std_out"] != "" or log["std_err"] != "" else "",
            "loglevel": "INFO",
            "timestamp": timestamp(),
            "message": "Task successful.",  # result._result['msg'] if "msg" in result._result else "Task successful.",
            "rel_file": global_playbook_path,
        }
        global_log_list.append(entry)

        if "RETURN".lower() == task.lower():
            self.finish_test(host_name=host_name)

    def v2_runner_on_failed(self, result,   *args, **kwargs):
        global global_return_value

        host_name = result._host.get_name()
        task = result._task.get_name()
        ignore_error = result._task_fields['ignore_errors'] if 'ignore_errors' in result._task_fields else False
        changed = result._result['changed'] if 'changed' in result._task_fields else None
        ## sometimes, std_out and std_err info is available inside result._result['stdout'] and 
        ## result._result['stderr'] respectively. Following lines were changed to represent it 
        # std_out = result._result['module_stdout'].split("\n") if 'module_stdout' in result._result else "N/A"
        # std_err = result._result['module_stderr'].split("\n") if 'module_stderr' in result._result else "N/A"
        if 'module_stdout' in result._result:
            std_out = result._result['module_stdout'].split("\n")
        elif 'stdout' in result._result:
            std_out = result._result['stdout'].split("\n")
        else:
            std_out = "N/A"
        if 'module_stderr' in result._result:
            std_err = result._result['module_stderr'].split("\n")
        elif 'stderr' in result._result:
            std_err = result._result['stderr'].split("\n")
        else:
            std_err = "N/A"
        exception = result._result['exception'].split("\n") if 'exception' in result._result else "N/A"
        error_msg = result._result['msg'].split("\n") if 'msg' in result._result else "N/A"
        return_code = result._result['rc'] if 'rc' in result._result else None

        if return_code == 3 and task == "Run server dependencies install script on Test":
            loglevel = "ERROR"
            global_return_value[host_name] = "FAILED"
            print("{0: <15} - FAILED: {1}".format(host_name, task))
        elif return_code == 3 or task == "Check if kubectl is installed" or task == "Check if Snap is installed" or task == "replace ip":
            loglevel = "INFO"
            global_return_value[host_name] = "OK"
            print("{0: <15} - OK: {1}".format(host_name, task))
        elif ignore_error or "test: " in task.lower():
            loglevel = "WARN"
            global_return_value[host_name] = "SKIPPED"
            print("{0: <15} - SKIPPED: {1}".format(host_name, task))
        elif return_code == 0:
            loglevel = "INFO"
            global_return_value[host_name] = "OK"
            print("{0: <15} - OK: {1}".format(host_name, task))
        else:
            loglevel = "ERROR"
            global_return_value[host_name] = "FAILED"
            print("{0: <15} - FAILED: {1}".format(host_name, task))

        if "results" in result._result:
            handle_loop_results(loop_results=result._result["results"], task_name=task, loglevel=loglevel, host_name=host_name)

        log_msg = {
            "host_name": host_name,
            "task": task,
            "ignore_error": ignore_error,
            "changed": changed,
            "std_out": std_out,
            "std_err": std_err,
            "exception": exception,
            "error_msg": error_msg,
            "return_code": return_code,
        }

        entry = {
            "suite": global_testsuite if not global_nested_testsuite else host_name,
            "test": global_testname,
            "step": task,
            "log": log_msg,
            "loglevel": loglevel,
            "timestamp": timestamp(),
            "message": error_msg,
            "rel_file": global_playbook_path,
        }
        global_log_list.append(entry)

        if global_return_value[host_name] == "FAILED":
            self.finish_test(host_name=host_name)

        if not ignore_error and "requires authentication" in exception or "identity/password/user/password" in exception:
            print("TASK FAILED: WRONG CREDENTIALS!")
        elif not ignore_error:
            print(json.dumps(entry, indent=4, sort_keys=True))


def execute(playbook_path, testsuite, testname, hosts, extra_vars=[]):
    global global_return_value, global_playbook_path, global_log_list, global_testsuite, global_nested_testsuite, global_testname, remote_user

    print("##################################################################################################################")
    print("##################################################################################################################")
    print("")
    print("STARTING PLAYBOOK: {}".format(playbook_path))
    print("")
    print("HOSTS: {}".format(hosts))
    print("SUITE: {}".format(testsuite))
    print("TEST:  {}".format(testname))
    print("")
    print("##################################################################################################################")

    global_return_value = {}
    global_log_list = []
    global_testsuite = testsuite
    global_nested_testsuite = False
    global_testname = testname
    global_playbook_path = playbook_path

    context.CLIARGS = ImmutableDict(
        connection="smart", verbosity=1, become_method="sudo")
    # connection='local', module_path=['/to/mymodules'], forks=10, become=None,become_method=None, become_user=None, check=False, diff=False)

    loader = DataLoader()
    passwords = dict(OS_PASSWORD='TESTPASSWORD')

    results_callback = ResultCallback()
    if len(hosts) == 1 and hosts[0] == "localhost":
        inventory = InventoryManager(loader=loader, sources=None)
    else:
        group_name = "os_server"
        inventory = InventoryManager(loader=loader, sources=None)
        inventory.add_group(group_name)
        for host in hosts:
            inventory.add_host(host=host, group=group_name)
            global_nested_testsuite = True

    variable_manager = VariableManager(loader=loader, inventory=inventory)

    play_source = loader.load_from_file(global_playbook_path)
    main_play_source = play_source[len(play_source)-1]

    if "vars_prompt" in main_play_source:
        main_play_source['vars_prompt'] = []

    if "vars" in main_play_source:
        if type(main_play_source['vars']) is not ans_objects.AnsibleSequence:
            main_play_source['vars'] = [main_play_source['vars']]

        for key, value in extra_vars.items():
            found = False
            for existing_var in main_play_source['vars']:
                if key in existing_var:
                    existing_var[key] = value
                    found = True

            if not found:
                main_play_source['vars'].append({key: value})

    else:
        print("No vars found!")
        # exit(1)
        main_play_source['vars'] = extra_vars

    play = Play().load(main_play_source, variable_manager=variable_manager, loader=loader)
    tqm = None
    try:
        tqm = TaskQueueManager(
            inventory=inventory,
            variable_manager=variable_manager,
            loader=loader,
            passwords=passwords,
            # Use our custom callback instead of the ``default`` callback plugin, which prints to stdout
            stdout_callback=results_callback
        )
        result = tqm.run(play)
    finally:
        if tqm is not None:
            tqm.cleanup()
        shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)

    tmp_return_value = "OK"
    for key, val in global_return_value.items():
        if val == "FAILED":
            tmp_return_value = "FAILED"
        else:
            tmp_return_value = val

    return tmp_return_value, global_log_list
