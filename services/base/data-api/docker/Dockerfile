FROM local-only/base-python-cpu:latest

LABEL IMAGE="data-api"
LABEL BUILD_IGNORE="False"

WORKDIR /app

COPY ./requirements.txt /app/
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt --no-cache-dir -r /app/requirements.txt

COPY ./ /app
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]