
FROM local-only/base-python-gpu:latest

LABEL IMAGE="nvflare-service"
LABEL VERSION="0.0.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt requirements.txt
RUN pip install -r requirements.txt

