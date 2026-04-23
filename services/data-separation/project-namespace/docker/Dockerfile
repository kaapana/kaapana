FROM local-only/base-python-cpu:latest

LABEL IMAGE="create-project-user"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY files/requirements.txt /kaapana/app/
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/ .
CMD ["python3","-u","create_project_user.py"]
