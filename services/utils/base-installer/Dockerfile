# base-installer only copies DAG/plugin/chart bundles into a mounted volume
# and pings Helm/Airflow via HTTP - it needs a plain python3 + requests +
# kaapana_client, nothing from the heavy base-python-cpu (torch, code-server,
# dcmtk, ...) that most other local-only bases carry.
FROM python:3.12-slim-bookworm

LABEL REGISTRY="local-only"
LABEL IMAGE="base-installer"
LABEL VERSION="latest"
LABEL BUILD_IGNORE="False"
LABEL BUILD_LIB_CONTEXT="True"

COPY --from=lib kaapana_client /lib/kaapana_client
COPY --from=constraints 0.7.0.txt /constraints.txt

RUN pip install --no-cache-dir -c /constraints.txt requests==2.32.3 /lib/kaapana_client

WORKDIR /kaapana/app

COPY files/run.py /kaapana/app/run.py

CMD ["python3","-u","/kaapana/app/run.py"]
