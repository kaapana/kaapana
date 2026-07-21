FROM local-only/base-python-cpu:latest

LABEL IMAGE="persist-model"
LABEL VERSION="0.2.1"
LABEL BUILD_IGNORE="False"

COPY files/requirements.txt /kaapana/requirements.txt
RUN pip3 install --upgrade pip && pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.7.0/constraints.txt --no-cache-dir -r /kaapana/requirements.txt

COPY files/processing-container.json /processing-container.json
COPY files/persist_model.py /kaapana/persist_model.py

CMD ["python3","-u","/kaapana/persist_model.py"]
