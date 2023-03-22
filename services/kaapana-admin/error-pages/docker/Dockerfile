FROM local-only/base-python-cpu:latest

LABEL IMAGE="error-pages"
LABEL VERSION="1.0.1"
LABEL CI_IGNORE="False"


WORKDIR /

COPY files/requirements.txt /requirements.txt
RUN pip install -c https://raw.githubusercontent.com/kaapana/kaapana/develop/build-scripts/constraints-0.1.3.txt --no-cache-dir -r requirements.txt && mkdir /error-server
COPY files/server.py /error-server/
COPY files/static /error-server/static
COPY files/templates /error-server/templates


EXPOSE 5000

CMD ["python","-u","/error-server/server.py"]
