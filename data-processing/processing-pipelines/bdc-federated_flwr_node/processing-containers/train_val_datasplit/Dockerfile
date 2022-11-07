FROM local-only/base-python-cpu:latest

LABEL IMAGE="train-val-datasplit"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/requirements.txt /kaapanasrc/requirements.txt

RUN pip install --upgrade pip && pip install -r /kaapanasrc/requirements.txt

COPY files/* /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/train_val_datasplit.py"]