FROM local-only/base-python-cpu:latest

LABEL IMAGE="otsus-method"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/ /kaapana/app/
CMD ["python3","-u","/kaapana/app/otsus_method.py"]