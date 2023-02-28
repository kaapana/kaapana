FROM local-only/base-nnunet:latest

LABEL IMAGE="nnunet-federated"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/ /kaapana/app/

CMD ["python3","-u","/kaapana/app/run_nnunet_federated.py"]