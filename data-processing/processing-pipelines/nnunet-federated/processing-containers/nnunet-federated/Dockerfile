FROM local-only/base-nnunet-v2:latest

LABEL IMAGE="nnunet-federated"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/ /kaapana/app/

CMD ["python3","-u","/kaapana/app/run_nnunet_federated.py"]