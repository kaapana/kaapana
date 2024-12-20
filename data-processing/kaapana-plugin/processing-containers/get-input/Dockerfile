FROM local-only/base-python-cpu:latest

LABEL IMAGE="get-input"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

WORKDIR /

COPY files/get_input.py /kaapana/app/

CMD ["python","-u","/kaapana/app/get_input.py"]