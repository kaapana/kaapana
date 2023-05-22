FROM local-only/base-python-cpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="base-installer"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install -c https://raw.githubusercontent.com/kaapana/kaapana/0.2.0/build-scripts/constraints-0.2.0.txt --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/run.py /kaapana/app/run.py

CMD ["python3","-u","/kaapana/app/run.py"]
