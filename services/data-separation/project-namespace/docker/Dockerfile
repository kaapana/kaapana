FROM local-only/base-python-cpu:latest

LABEL IMAGE="create-project-user"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="False"

COPY files/ .
CMD ["python3","-u","create_project_user.py"]
