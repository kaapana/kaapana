FROM local-only/base-python-cpu:latest

LABEL IMAGE="classification-preprocessing"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

RUN apt-get update && apt-get install -y xvfb

COPY files/requirements.txt /kaapana/requirements.txt
RUN pip3 install --upgrade pip && pip install -c https://raw.githubusercontent.com/kaapana/kaapana/0.2.1/build-scripts/constraints-0.2.1.txt --no-cache-dir -r /kaapana/requirements.txt

COPY files/* /kaapana/

CMD ["python3","-u","/kaapana/classification_preprocessing.py"]
