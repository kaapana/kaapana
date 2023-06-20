FROM local-only/base-python-cpu:latest

LABEL IMAGE="advanced-collect-metadata-federated"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/ /kaapana/app/

CMD ["python3","-u","/kaapana/app/run_acmd_federated.py"]