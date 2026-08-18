FROM local-only/base-python-cpu:latest

LABEL IMAGE="hello-world"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt requirements.txt
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN pip install -c /constraints.txt -r requirements.txt

COPY files/ ./
RUN chmod +x boot.sh

ENV FLASK_APP run.py

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]