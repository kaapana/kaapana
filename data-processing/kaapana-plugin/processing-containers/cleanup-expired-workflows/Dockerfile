FROM local-only/base-python-cpu:latest

LABEL IMAGE="cleanup-expired-workflows"
LABEL BUILD_IGNORE="False"

COPY files/ /kaapana/app/

CMD ["python3","-u","/kaapana/app/process.py"]
