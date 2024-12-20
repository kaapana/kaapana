FROM local-only/base-python-cpu:latest

LABEL IMAGE="service-checker"
LABEL VERSION="1.1"
LABEL BUILD_IGNORE="False"

COPY files/service_checker.py /service_checker.py

CMD [ "python3", "-u","/service_checker.py" ]
