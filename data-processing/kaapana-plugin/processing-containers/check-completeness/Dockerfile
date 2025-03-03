FROM local-only/base-python-cpu:latest

LABEL IMAGE="check-completeness"
LABEL VERSION="0.4.0"
LABEL BUILD_IGNORE="False"

COPY files/* /kaapana/app/

CMD ["python3", "-u", "/kaapana/app/check-completeness.py"]