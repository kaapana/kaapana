FROM local-only/base-python-cpu:latest

LABEL IMAGE="service-checker"
LABEL VERSION="1.1"
LABEL CI_IGNORE="False"

RUN pip install -c https://raw.githubusercontent.com/kaapana/kaapana/0.2.0/build-scripts/constraints-0.2.0.txt requests==2.27.1

COPY files/service_checker.py /service_checker.py

CMD [ "python3", "-u","/service_checker.py" ]
