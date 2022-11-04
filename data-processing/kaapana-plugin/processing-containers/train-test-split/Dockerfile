FROM local-only/base-python-cpu:latest

LABEL IMAGE="train-test-split"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/ /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/run_train_test_split.py"]