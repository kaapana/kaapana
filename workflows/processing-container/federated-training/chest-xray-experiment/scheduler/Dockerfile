FROM nvcr.io/nvidia/pytorch:20.09-py3

LABEL IMAGE="federated-exp-chest-xray-train"
LABEL VERSION="0.1.0-vdev"
LABEL CI_IGNORE="True"

WORKDIR /

COPY files/* /

#CMD tail -f  /dev/null
CMD ["python3","-u","/process.py"]