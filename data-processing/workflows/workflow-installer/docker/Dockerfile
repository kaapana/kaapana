FROM python:3.11-slim

LABEL IMAGE="workflow-installer"
LABEL BUILD_IGNORE="False"

# Branch name for workflow-cli installation (can be overridden at build time)
ARG BRANCH_NAME=master

WORKDIR /kaapana/app

# Install git for pip to clone from repository
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt /kaapana/app/requirements.txt.template
RUN sed "s|@BRANCH_NAME@|@${BRANCH_NAME}|g" /kaapana/app/requirements.txt.template > /kaapana/app/requirements.txt && \
    python -m pip install --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/* /kaapana/app/

CMD ["python", "-u", "/kaapana/app/workflow_installer.py"]
