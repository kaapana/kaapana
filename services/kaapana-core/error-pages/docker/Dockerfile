FROM python:3.9-alpine3.12

LABEL IMAGE="error-pages"
LABEL VERSION="1.0.1"
LABEL CI_IGNORE="False"


WORKDIR /

COPY files/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir /error-server
ADD files/server.py /error-server/
ADD files/static /error-server/static
ADD files/templates /error-server/templates


EXPOSE 5000

CMD ["python","-u","/error-server/server.py"]
