FROM local-only/base-python-cpu:latest

LABEL IMAGE="auth-backend"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY ./files/requirements.txt /kaapana/app/requirements.txt
RUN pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt --no-cache-dir --upgrade -r /kaapana/app/requirements.txt

COPY ./files/*.py /kaapana/app/
COPY ./files/*.html /kaapana/app/

RUN curl -L -o opa https://openpolicyagent.org/downloads/v0.56.0/opa_linux_amd64_static
RUN chmod 755 ./opa

COPY files/bundle/ bundle/
RUN mkdir -p /kaapana/app/authz 
RUN ./opa build -b bundle/ -o authz/endpoints.tar.gz

### DEVELOP
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]

### PRODUCTION
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
