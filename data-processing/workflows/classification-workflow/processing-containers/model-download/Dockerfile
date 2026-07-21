FROM local-only/base-python-cpu:latest

LABEL IMAGE="model-download"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/requirements.txt /kaapana/requirements.txt
RUN pip3 install --upgrade pip && pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.7.0/constraints.txt --no-cache-dir -r /kaapana/requirements.txt

COPY files/processing-container.json /processing-container.json
COPY files/model_download.py /kaapana/model_download.py

CMD ["python3","-u","/kaapana/model_download.py"]
