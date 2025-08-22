FROM local-only/base-python-cpu:latest

LABEL IMAGE="migration"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana

COPY files/migration.py ./

CMD ["python3", "/kaapana/migration.py"] 
