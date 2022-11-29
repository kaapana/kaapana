# # With cuda
# FROM nvcr.io/nvidia/pytorch:20.09-py3

# Without cuda
FROM local-only/base-python-alpine:latest

LABEL IMAGE="bash-template"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="True"

COPY files/process.sh /

CMD ["/bin/sh", "/process.sh"]