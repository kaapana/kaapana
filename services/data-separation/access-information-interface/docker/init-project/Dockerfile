FROM local-only/base-python-cpu:latest

LABEL IMAGE="init-projects"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="False"


COPY files/init-projects.py .
COPY files/KeycloakHelper.py .

CMD ["python3", "-u", "init-projects.py"]