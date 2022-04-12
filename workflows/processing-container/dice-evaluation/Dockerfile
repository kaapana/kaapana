FROM local-only/base-pytorch-cpu:0.1.0

LABEL IMAGE="dice-evaluation"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r requirements.txt

COPY files/start.py /kaapanasrc/

CMD ["python3", "-m", "/kaapanasrc/start.py"]