FROM local-only/base-python-cpu:latest

LABEL IMAGE="get-ref-series"
LABEL VERSION="v1.2.4"
LABEL BUILD_IGNORE="False"

COPY files/get-ref-series.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/get-ref-series.py"]