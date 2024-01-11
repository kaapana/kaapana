FROM local-only/base-python-cpu:latest

LABEL IMAGE="service-checker"
LABEL VERSION="1.1"
LABEL BUILD_IGNORE="False"

RUN pip install -c https://raw.githubusercontent.com/hammb/kaapana-constraints/main/constraints-0.2.6.txt requests==2.27.1

COPY files/service_checker.py /service_checker.py

CMD [ "python3", "-u","/service_checker.py" ]
