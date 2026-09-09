FROM local-only/base-python-cpu:latest

LABEL IMAGE="data-api"
LABEL BUILD_IGNORE="False"

WORKDIR /app

COPY ./requirements.txt /app/
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN python -m pip install -c /constraints.txt --no-cache-dir -r /app/requirements.txt

COPY ./ /app
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]