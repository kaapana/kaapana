FROM local-only/base-python-gpu:latest

LABEL IMAGE="classification-inference"
LABEL VERSION="0.2.1"
LABEL BUILD_IGNORE="False"

RUN apt-get update && apt-get install -y xvfb

COPY files/requirements.txt /kaapana/requirements.txt
RUN pip3 install --upgrade pip && pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt --no-cache-dir -r /kaapana/requirements.txt

COPY files/* /kaapana/

CMD ["python3","-u","/kaapana/inference.py"]
