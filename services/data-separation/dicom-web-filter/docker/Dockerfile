FROM local-only/base-python-cpu:latest

LABEL IMAGE="dicom-web-filter"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

RUN apt-get update

WORKDIR /app

COPY files/requirements.txt /app/
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt --no-cache-dir -r /app/requirements.txt

COPY files/ /app
# RUN chmod +x /app/boot.sh Deliberate mistake for CI reporting

CMD ["/bin/sh", "/app/boot.sh"]