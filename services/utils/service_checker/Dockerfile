FROM local-only/base-python-cpu:latest

LABEL IMAGE="service-checker"
LABEL VERSION="1.1"
LABEL CI_IGNORE="False"

RUN pip install -c https://raw.githubusercontent.com/kaapana/kaapana/develop/build-scripts/constraints-0.1.3.txt requests==2.27.1

COPY files/service_checker.py /service_checker.py

CMD [ "python3", "-u","/service_checker.py" ]
