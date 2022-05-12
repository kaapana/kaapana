FROM python:3.9-alpine3.12

LABEL IMAGE="service_checker"
LABEL VERSION="1.1"
LABEL CI_IGNORE="False"

RUN pip install requests==2.27.1

COPY files/service_checker.py /service_checker.py

CMD [ "python3", "-u","/service_checker.py" ]
