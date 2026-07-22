FROM local-only/base-python-cpu:latest

LABEL IMAGE="head-demo-tools"
LABEL VERSION="1.0.0"
LABEL BUILD_IGNORE="False"

COPY processing-container.json /
COPY files/demo_tools.py /kaapana/app/demo_tools.py

WORKDIR /kaapana/app

