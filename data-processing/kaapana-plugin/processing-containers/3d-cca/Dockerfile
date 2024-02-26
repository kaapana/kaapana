FROM local-only/base-python-cpu:latest

LABEL IMAGE="cca"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r /requirements.txt

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/start.py"]
