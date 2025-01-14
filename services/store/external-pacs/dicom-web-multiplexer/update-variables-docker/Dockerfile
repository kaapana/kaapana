FROM local-only/base-python-cpu:latest

LABEL IMAGE="update-variables"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

COPY files/start.sh /app/start.sh
RUN chmod +x /app/start.sh
ENTRYPOINT ["/app/start.sh"]