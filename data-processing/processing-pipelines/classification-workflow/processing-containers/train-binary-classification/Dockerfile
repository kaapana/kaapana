FROM local-only/base-python-gpu:latest

LABEL IMAGE="classification-training"
LABEL VERSION="0.2.0"
LABEL CI_IGNORE="False"

RUN apt-get update && apt-get install -y xvfb

COPY files/requirements.txt /kaapana/requirements.txt
RUN pip3 install --upgrade pip && pip install -r /kaapana/requirements.txt

COPY files/* /kaapana/

CMD ["python3","-u","/kaapana/training.py"]
