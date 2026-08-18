FROM local-only/base-python-cpu:latest

LABEL IMAGE="workflow-api"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="False"

WORKDIR /app

COPY files/requirements.txt /app/
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN python -m pip install -c /constraints.txt --no-cache-dir -r /app/requirements.txt

COPY files/ /app
RUN chmod +x /app/boot.sh

CMD ["/app/boot.sh"]