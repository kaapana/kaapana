FROM local-only/base-python-cpu:latest

LABEL IMAGE="train-val-datasplit"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/requirements.txt /app/requirements.txt

RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY files/* /app/

CMD ["python3","-u","/app/train_val_datasplit.py"]