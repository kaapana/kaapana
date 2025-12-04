FROM python:3.11-slim

LABEL IMAGE="workflow-installer"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/* /kaapana/app/

CMD ["python", "-u", "/kaapana/app/workflow_installer.py"]
