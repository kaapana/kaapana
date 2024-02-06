FROM local-only/base-python-gpu:latest

#For this project codeserver is only available as extension and not in every pod to debug:
# Code server
RUN wget https://code-server.dev/install.sh
RUN /bin/bash install.sh --version 4.2.0
RUN code-server --install-extension ms-python.python

LABEL IMAGE="code-server"
LABEL VERSION="4.2.0"
LABEL CI_IGNORE="False"
