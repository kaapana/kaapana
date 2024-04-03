FROM local-only/base-python-cpu:latest

LABEL IMAGE="send-to-faiss"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

RUN apt-get update && apt-get install -y xvfb

COPY files/requirements.txt /kaapana/requirements.txt
RUN pip3 install --upgrade pip && pip3 install -r /kaapana/requirements.txt

COPY files/* /kaapana/

CMD ["python3","-u","/kaapana/send_to_faiss.py"]
