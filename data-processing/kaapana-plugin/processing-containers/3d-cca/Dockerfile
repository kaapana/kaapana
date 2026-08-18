FROM local-only/base-python-cpu:latest

LABEL IMAGE="cca"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN pip3 install -c /constraints.txt --no-cache-dir -r /requirements.txt

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/start.py"]
