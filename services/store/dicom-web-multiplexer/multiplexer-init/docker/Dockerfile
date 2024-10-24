FROM local-only/base-python-cpu:latest

LABEL IMAGE="multiplexer-init"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /

COPY files/start.py /start.py

ENTRYPOINT ["python", "/start.py"]
