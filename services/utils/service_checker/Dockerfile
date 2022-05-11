FROM local-only/base-python-alpine:0.1.0

LABEL IMAGE="service_checker"
LABEL VERSION="1.1"
LABEL CI_IGNORE="False"

COPY files/service_checker.py /service_checker/service_checker.py

CMD [ "python3", "-u","/service_checker/service_checker.py" ]
