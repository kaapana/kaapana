FROM local-only/base-python-cpu:latest

LABEL IMAGE="kaapana-backend"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt

RUN apt-get update && apt-get install -y ldap-utils  && rm -rf /var/lib/apt/lists/* 

COPY files/ /kaapana/app
RUN chmod +x /kaapana/app/boot.sh

CMD ["/bin/sh", "/kaapana/app/boot.sh"]