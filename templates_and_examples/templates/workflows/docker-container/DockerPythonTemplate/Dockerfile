# # With cuda
# FROM nvcr.io/nvidia/pytorch:20.09-py3

# Without cuda
FROM python:3.9-alpine3.12

LABEL IMAGE="python-template"
LABEL VERSION="0.1-vdev"
LABEL CI_IGNORE="True"

COPY files/process.py /

CMD ["python3","-u","/process.py"]