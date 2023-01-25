FROM local-only/base-python-cpu:latest

LABEL IMAGE="m2olie-backend"
LABEL VERSION="0.0.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/ /kaapana/app
RUN chmod +x /kaapana/app/boot.sh

ENTRYPOINT ["/kaapana/app/boot.sh"]