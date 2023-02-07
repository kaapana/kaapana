FROM local-only/base-python-cpu:latest

LABEL IMAGE="train-test-split"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /app
COPY files/* /app/

CMD ["python3","-u","/app/run_train_test_split.py"]