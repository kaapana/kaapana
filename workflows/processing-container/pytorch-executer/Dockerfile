# FROM nvidia/cuda:10.2-runtime-ubuntu18.04
FROM nvcr.io/nvidia/pytorch:20.09-py3

LABEL IMAGE="pytorch-executer"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

# Common Python packages
COPY files/requirements.txt /root/
RUN pip3 install -r /root/requirements.txt

COPY files/run.sh /root/

CMD ["/bin/bash", "/root/run.sh"]

