FROM local-only/base-python-cpu:latest

LABEL IMAGE="keycloak-init"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="False"

COPY files/ .
CMD ["python3","-u","configure_realm.py"]
