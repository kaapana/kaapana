FROM local-only/base-python-cpu:latest

LABEL IMAGE="workflow-cleaner"
LABEL BUILD_IGNORE="False"

COPY files/ /kaapana/app/

CMD ["python3","-u","/kaapana/app/process.py"]
