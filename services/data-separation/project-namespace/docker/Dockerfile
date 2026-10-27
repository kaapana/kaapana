FROM local-only/base-python-cpu:latest

LABEL IMAGE="create-project-user"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY --from=constraints 0.7.0.txt /constraints.txt
COPY files/requirements.txt /kaapana/app/
RUN python -m pip install -c /constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/ .
CMD ["python3","-u","create_project_user.py"]
