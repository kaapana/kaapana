FROM python:3.9-alpine3.12

LABEL IMAGE="scanparam2json"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="True"

COPY files/requirements.txt /
RUN pip3 install -r requirements.txt

COPY files/scanparam2json.py /

CMD ["python3","-u","/scanparam2json.py"]