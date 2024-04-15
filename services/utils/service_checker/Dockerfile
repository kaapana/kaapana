FROM local-only/base-python-cpu:latest

LABEL IMAGE="service-checker"
LABEL VERSION="1.1"
LABEL BUILD_IGNORE="False"

RUN pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt requests==2.31.0

COPY files/service_checker.py /service_checker.py

CMD [ "python3", "-u","/service_checker.py" ]
