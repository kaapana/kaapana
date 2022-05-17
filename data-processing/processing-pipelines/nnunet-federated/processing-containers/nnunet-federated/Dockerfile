FROM local-only/base-nnunet-gpu:03-22

LABEL IMAGE="nnunet-federated"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/ /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/run_nnunet_federated.py"]