FROM local-only/base-python-cpu:latest

LABEL IMAGE="pyradiomics"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python3 -m pip install -c https://raw.githubusercontent.com/hammb/kaapana-constraints/main/constraints-0.2.6.txt --no-cache-dir -r /kaapana/app/requirements.txt && rm /kaapana/app/requirements.txt 

COPY files/pyradiomics.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/pyradiomics.py"]
