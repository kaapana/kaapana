FROM local-only/base-nnunet:latest

LABEL IMAGE="nnunet-federated"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/ /app/

CMD ["python3","-u","/app/run_nnunet_federated.py"]