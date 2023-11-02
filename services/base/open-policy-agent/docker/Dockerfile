FROM docker.io/openpolicyagent/opa:0.56.0

LABEL IMAGE="open-policy-agent"
LABEL VERSION="0.0.1"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/opa/

COPY files/config.yaml /kaapana/opa/

### Development
#CMD ["run", "--server","--log-format=json-pretty", "--set=decision_logs.console=true", "-c", "config.yaml"]

### Production
CMD ["run", "--server", "-c", "config.yaml"]
