FROM local-only/base-python-cpu:latest

LABEL IMAGE="train-val-datasplit"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/requirements.txt /kaapana/app/

RUN pip install --upgrade pip && pip install -c https://raw.githubusercontent.com/kaapana/kaapana/0.2.0/build-scripts/constraints-0.2.0.txt -r /kaapana/app/requirements.txt

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/train_val_datasplit.py"]