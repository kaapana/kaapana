FROM local-only/base-python-cpu:latest

LABEL IMAGE="dice-evaluation"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r /requirements.txt

COPY files/start.py /app/

CMD ["python3", "-u", "/app/start.py"]