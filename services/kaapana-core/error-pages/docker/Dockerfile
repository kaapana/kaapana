FROM python:3.4-alpine3.7

LABEL IMAGE="error-pages"
LABEL VERSION="1.0.1"
LABEL CI_IGNORE="False"


WORKDIR /

RUN pip install --upgrade pip
COPY files/requirements.txt /requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir /error-server
ADD files/server.py /error-server/
ADD files/static /error-server/static
ADD files/templates /error-server/templates


EXPOSE 5000

CMD ["python","-u","/error-server/server.py"]
