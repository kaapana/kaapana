FROM local-only/base-python-cpu:latest

LABEL IMAGE="federated-setup-central-test"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/ /app/

CMD ["python3","-u","/app/run_federated_setup_central_test.py"]