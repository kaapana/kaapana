FROM local-only/base-python-cpu:latest

LABEL IMAGE="train-test-split"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app
COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/run_train_test_split.py"]