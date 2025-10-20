FROM local-only/base-python-cpu:latest

LABEL IMAGE="migration"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/migration.py"]