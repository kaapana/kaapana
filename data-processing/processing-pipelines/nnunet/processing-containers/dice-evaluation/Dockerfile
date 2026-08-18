FROM local-only/base-python-cpu:latest

LABEL IMAGE="dice-evaluation"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

COPY files/requirements.txt /
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN pip3 install -c /constraints.txt --no-cache-dir -r /requirements.txt

COPY files/start.py /kaapana/app/

CMD ["python3", "-u", "/kaapana/app/start.py"]