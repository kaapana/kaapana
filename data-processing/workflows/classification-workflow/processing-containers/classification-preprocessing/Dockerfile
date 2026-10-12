FROM local-only/base-python-cpu:latest

LABEL IMAGE="classification-preprocessing-task"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

RUN apt-get update && apt-get install -y xvfb

COPY files/requirements.txt /kaapana/requirements.txt
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN pip3 install --upgrade pip && pip install -c /constraints.txt --no-cache-dir -r /kaapana/requirements.txt

COPY files/processing-container.json /processing-container.json
COPY files/classification_preprocessing.py /kaapana/preprocess.py

CMD ["python3","-u","/kaapana/preprocess.py"]
