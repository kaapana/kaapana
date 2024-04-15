FROM local-only/base-python-cpu:latest

LABEL IMAGE="radiomics-federated"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/ /kaapana/app/

CMD ["python3","-u","/kaapana/app/run_radiomics_federated.py"]
