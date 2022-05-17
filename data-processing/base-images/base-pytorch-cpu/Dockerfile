FROM local-only/base-python-cpu:0.1.0

LABEL REGISTRY="local-only"
LABEL IMAGE="base-pytorch-cpu"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/requirements.txt /root/
RUN python -m pip install --upgrade pip && pip3 install -r /root/requirements.txt