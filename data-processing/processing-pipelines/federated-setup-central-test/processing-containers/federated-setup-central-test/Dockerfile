FROM local-only/base-python-cpu:latest

LABEL IMAGE="federated-setup-central-test"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/ /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/run_federated_setup_central_test.py"]