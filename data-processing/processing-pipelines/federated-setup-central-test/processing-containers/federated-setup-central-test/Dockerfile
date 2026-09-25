# base-python-gpu: this image needs torch (kaapana_federated / monai), which the CPU base no longer carries.
FROM local-only/base-python-gpu:latest

LABEL IMAGE="federated-setup-central-test"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/ /kaapana/app/

CMD ["python3","-u","/kaapana/app/run_federated_setup_central_test.py"]