FROM local-only/base-python-gpu:latest

LABEL IMAGE="classification-task"
LABEL BUILD_IGNORE="False"

RUN apt-get update && apt-get install -y xvfb

COPY files/requirements.txt /kaapana/requirements.txt
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN pip3 install --upgrade pip && pip install -c /constraints.txt --no-cache-dir -r /kaapana/requirements.txt

COPY files/processing-container.json /processing-container.json
COPY files/preprocess.py /kaapana/preprocess.py
COPY files/training.py /kaapana/training.py
COPY files/inference.py /kaapana/inference.py
COPY files/batchgenerators_dataloader.py /kaapana/batchgenerators_dataloader.py
COPY files/opensearch_helper.py /kaapana/opensearch_helper.py
