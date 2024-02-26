FROM local-only/base-python-cpu:latest

LABEL IMAGE="download-zenodo-models"
LABEL VERSION="0.1.1"
LABEL BUILD_IGNORE="False"

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/start.py"]