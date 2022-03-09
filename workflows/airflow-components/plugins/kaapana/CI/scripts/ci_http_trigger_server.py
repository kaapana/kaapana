#!/usr/bin/env python3

from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib
import logging
import time
# from threading import Thread
import subprocess
from git import Repo
import os
import signal

global ci_dir, git_dir, last_trigger

ci_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
git_dir = '/home/ubuntu/kaapana'

class S(BaseHTTPRequestHandler):

    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        global git_dir, ci_dir
        self._set_response()
        urllib_path = urllib.parse.urlparse(self.path)
        parameters = urllib.parse.parse_qs(
            urllib_path.query, keep_blank_values=True)

        # self.wfile.write("Parameters {} found. <br />".format(parameters).encode('utf-8'))

        print("###################################################  IN GET: {}".format(
            urllib_path.path))
        if "/favicon.ico" in self.path:
            self.wfile.write("ok".encode('utf-8'))
            return

        print("IN GET {}".format(urllib_path.path))
        path_parts = urllib_path.path.split("/")
        if path_parts[1] == "cikaapana":
            lock_file = os.path.join(os.path.dirname(ci_dir), "ci_running.txt")

            if path_parts[2] == "terminate" and os.path.isfile(lock_file):
                with open(lock_file) as f:
                    pid = f.read()
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    self.wfile.write("Terminated CI run: {}".format(pid).encode('utf-8'))
                except Exception as e:
                    print(e)
                    os.remove(lock_file)
                    self.wfile.write("Removed lock_file since no process {} found.".format(pid).encode('utf-8'))
                    
            elif path_parts[2] != "terminate" and os.path.isfile(lock_file):
                print("CI pipeline already running!")
                print("The lock_file is present: {}".format(lock_file))
                self.wfile.write("CI pipeline already running...".encode('utf-8'))

            elif path_parts[2] == "terminate" and not os.path.isfile(lock_file):
                print("There is no CI pipeline running right now...")
                self.wfile.write("There is no CI pipeline running right now...".encode('utf-8'))

            else:
                print("cikaapana ok..")

                if "&" in urllib_path.path:
                    self.wfile.write("start parameters with ? !".encode('utf-8'))
                    return

                if "bugfix" == path_parts[-2] or "hotfix" == path_parts[-2] or "feature" == path_parts[-2]:
                    branch = path_parts[-2]+"/"+path_parts[-1]
                else:
                    branch = path_parts[-1]

                print("branch: {}".format(branch))

                ci_paras = []
                if "delete-instances" in parameters:
                    ci_paras.append("--delete-instances")
                    del parameters["delete-instances"]

                if "os-usr" in parameters:
                    ci_paras.append("--username")
                    ci_paras.append(f"{parameters['os-usr'][0]}")
                    del parameters["os-usr"]
                else:
                    self.wfile.write("CI pipeline can't be triggered without openstack user <br />".encode('utf-8'))
                
                if "os-pwd" in parameters:
                    ci_paras.append("--password")
                    ci_paras.append(f"{parameters['os-pwd'][0]}")
                    del parameters["os-pwd"]
                else:
                    self.wfile.write("CI pipeline can't be triggered without openstack password <br />".encode('utf-8'))

                if "reg-url" in parameters:
                    ci_paras.append("--registry-url")
                    ci_paras.append(f"{parameters['reg-url'][0]}")
                    del parameters["reg-url"]
                else:
                    self.wfile.write("CI pipeline can't be triggered without registry URL <br />".encode('utf-8'))
                
                if "reg-usr" in parameters:
                    ci_paras.append("--registry-username")
                    ci_paras.append(f"{parameters['reg-usr'][0]}")
                    del parameters["reg-usr"]
                else:
                    self.wfile.write("CI pipeline can't be triggered without registry username <br />".encode('utf-8'))
                
                if "reg-pwd" in parameters:
                    ci_paras.append("--registry-password")
                    ci_paras.append(f"{parameters['reg-pwd'][0]}")
                    del parameters["reg-pwd"]
                    # self.wfile.write("ci_paras {} found. <br />".format(ci_paras).encode('utf-8'))
                else:
                    self.wfile.write("CI pipeline can't be triggered without registry password/token <br />".encode('utf-8'))
                
                if "launch-name" in parameters:
                    ci_paras.append("--launch-name")
                    ci_paras.append(f"{parameters['launch-name'][0]}")
                    del parameters["launch-name"]
                
                if "email-notifications" in parameters:
                    ci_paras.append("--email-notifications")
                    del parameters["email-notifications"]

                if "charts-only" in parameters:
                    ci_paras.append("--charts-only")
                    del parameters["charts-only"]

                if "container-only" in parameters:
                    ci_paras.append("--container-only")
                    del parameters["container-only"]

                if "build-only" in parameters:
                    ci_paras.append("--build-only")
                    del parameters["build-only"]

                if "deploy-only" in parameters:
                    ci_paras.append("--deployment-only")
                    del parameters["deploy-only"]
                
                if "disable-report" in parameters:
                    ci_paras.append("--disable-report")
                    del parameters["disable-report"]
    
                if len(parameters) > 0:
                    self.wfile.write("Unsupported parameters: {}".format(
                        list(parameters.keys())).encode('utf-8'))
                    return

                repo = Repo(git_dir)
                all_branches = repo.git.branch('-a').split("\n")
                all_branches = [h.replace(
                    "*", " ").split("  ")[1].replace("remotes/origin/", "") for h in all_branches]

                if not any(branch == c for c in all_branches):
                    repo.remote().fetch()
                    all_branches = repo.git.branch('-a').split("\n")
                    all_branches = [h.replace("*", " ").split("  ")[1].replace("remotes/origin/", "") for h in all_branches]

                if any(branch == c for c in all_branches):
                    print("starting ci for: {}".format(branch))
                    self.wfile.write("Triggered!".encode('utf-8'))

                    ci_paras.append("--branch")
                    ci_paras.append("{}".format(branch))
                    ci_paras.append("--disable-safe-mode")
                    start_ci_pipeline_file = os.path.join(ci_dir, "CI", "scripts", "start_ci_pipeline.py")
                    my_env = os.environ.copy()
                    my_env["PATH"] = "/home/ubuntu/.local/bin:/usr/bin:/bin:/snap/bin:/usr/local/bin:" + my_env["PATH"]
                    p = subprocess.Popen(["/usr/bin/python3", start_ci_pipeline_file, *ci_paras], env=my_env)

                else:
                    self.wfile.write("""
                    <html>
                    <head>
                        <title>Kaapana CI</title>
                    </head>
                    <body>
                        <TABLE ALIGN=CENTER WIDTH=60%>
                            <TR>
                                <TD>
                                <FONT SIZE=6>
                                    <H1 ALIGN=CENTER >
                                        <FONT FACE="COMIC SANS, COMIC RELIEF, PAPYRUS, CURSIVE">
                                            <BLINK>
                                            <MARQUEE BEHAVIOR=ALTERNATE><B>Kaapana CI!</B></MARQUEE>
                                            </BLINK>
                                        </FONT>
                                    </H1>
                                </FONT>
                                </TD>
                            </TR>
                        </TABLE>
                        <TABLE WIDTH=100% BGCOLOR=CORNSILK>
                            <TR>
                                <TD>
                                <TABLE>
                                    <TR>
                                        <TD VALIGN=TOP>
                                            <div>
                                            <h1><strong>Branch {} not found!</strong></h1>
                                            <br />
                                            <h2>Usage:</h2>
                                            <h2>/cikaapana/&lt;branch&gt;?para1&amp;para2</h2>
                                            <br />
                                            <div><strong>where para could be:</strong></div>
                                            <br />
                                            <div>&nbsp; &nbsp; delete-instances&nbsp; &nbsp; &nbsp; &nbsp; -&gt; delete OpenStack ci deployment instances first if available</div>
                                            <div>&nbsp; &nbsp; os-usr&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; -&gt; OpenStack CI user "os-usr=&ltos-ci-user&gt"</div>
                                            <div>&nbsp; &nbsp; os-pwd&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; -&gt; OpenStack CI password "os-pwd=&ltos-ci-password/token&gt"</div>
                                            <div>&nbsp; &nbsp; reg-url&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; -&gt; container registry url "reg-url=&lturl_link&gt"</div>
                                            <div>&nbsp; &nbsp; reg-usr&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; -&gt; container registry user "reg-usr=&ltreg_user&gt"</div>
                                            <div>&nbsp; &nbsp; reg-pwd&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; -&gt; enter container registry token/password "reg-pwd=&ltreg-password/token&gt"</div>
                                            <div>&nbsp; &nbsp; launch-name&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; -&gt; CI job launch name, appears on CI dashboard</div>
                                            <div>&nbsp; &nbsp; build-only&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; -&gt; check, build and push Helm charts Docker containers only</div>
                                            <div>&nbsp; &nbsp; charts-only&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; -&gt; check, build and push Helm charts only</div>
                                            <div>&nbsp; &nbsp; docker-only&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; -&gt; check, build and push Docker containers only</div>
                                            <div>&nbsp; &nbsp; deploy-only&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; -&gt; platform deployment tests only</div>
                                            <div>&nbsp; &nbsp; disable-report&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; -&gt; disable reporting on CI dashboard</div>
                                            <div>&nbsp; &nbsp; email-notifications&nbsp; &nbsp; -&gt; enable email-notifications for errors</div>
                                            <br />
                                            <div><strong>example:</strong></div>
                                            <div><em>/cikaapana/develop?delete-instances&amp;build-only&amp;email-notifications</em></div>
                                            <br />
                                            <h2>To terminate a running ci run: /cikaapana/terminate</h2>
                                            </div>
                                        </TD>
                                    </TR>
                                </TABLE>
                                </TD>
                            </TR>
                        </TABLE>
                    </body>
                    </html>

                    """.format(branch).encode('utf-8'))

        else:
            self.wfile.write("Nothing to do...".encode('utf-8'))

    def do_POST(self):
        # <--- Gets the size of data
        content_length = int(self.headers['Content-Length'])
        # <--- Gets the data itself
        post_data = self.rfile.read(content_length)
        logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                     str(self.path), str(self.headers), post_data.decode('utf-8'))

        self._set_response()
        self.wfile.write("POST request for {}".format(
            self.path).encode('utf-8'))


def run(server_class=HTTPServer, handler_class=S, port=8080):
    logging.basicConfig(level=logging.INFO)
    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')

def cronjob_execute():
    ci_paras = []
    ci_paras.append("--delete-instances")
    ci_paras.append("--email-notifications")
    # ci_paras.append("--charts-only")
    # ci_paras.append("--container-only")
    # ci_paras.append("--build-only")
    # ci_paras.append("--deployment-only")

    S.start_ci(branch="develop",ci_paras=ci_paras)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-m", "--mode", dest="mode",  default="server",help="server - ci-http-server | cronjob - cronjob-executor")
    parser.add_argument("-p", "--port", dest="port",  default=8080,help="Port of the http server to listen on.")
    args = parser.parse_args()
    port = args.port
    mode = args.mode

    if mode == "server":
        print("###################################################  Starting CI HTTP SERVER")
        print("###################################################  Parameters: delete-instances,os-usr,os-pwd,reg-url,reg-usr,reg-pwd,launch-name,email-notifications,charts-only,container-only,build-only,deploy-only,disable-report")
        run(port=int(port))
    elif mode == "cronjob":
        cronjob_execute()
    else:
        print("mode: {} not supported.")
        print("options: server | cronjob")
        exit(1)
