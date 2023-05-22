FROM local-only/base-python-cpu:latest

LABEL IMAGE="pyradiomics"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python3 -m pip install -c https://raw.githubusercontent.com/kaapana/kaapana/0.2.0/build-scripts/constraints-0.2.0.txt --no-cache-dir -r /kaapana/app/requirements.txt && rm /kaapana/app/requirements.txt 

COPY files/pyradiomics.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/pyradiomics.py"]
