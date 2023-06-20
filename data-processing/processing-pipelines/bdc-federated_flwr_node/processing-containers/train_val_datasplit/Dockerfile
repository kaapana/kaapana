FROM local-only/base-python-cpu:latest

LABEL IMAGE="train-val-datasplit"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/train_val_datasplit.py"]