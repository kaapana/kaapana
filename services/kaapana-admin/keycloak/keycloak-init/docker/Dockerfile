FROM local-only/base-python-cpu:latest

LABEL IMAGE="keycloak-init"
LABEL BUILD_IGNORE="False"

COPY files/ .
CMD ["python3","-u","configure_realm.py"]
