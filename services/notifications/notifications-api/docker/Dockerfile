FROM local-only/base-python-cpu:latest

LABEL IMAGE="notifications-api"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /app

COPY files/requirements.txt /app/
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt --no-cache-dir -r /app/requirements.txt

COPY files/ /app
RUN chmod +x /app/boot.sh

CMD ["/app/boot.sh"]