FROM docker.io/openpolicyagent/opa:1.18.2

LABEL IMAGE="open-policy-agent"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/opa/

COPY files/config.yaml /kaapana/opa/

### Development
#CMD ["run", "--server", "--v0-compatible", "--log-format=json-pretty", "--set=decision_logs.console=true", "-c", "config.yaml"]

### Production
# --v0-compatible: use to ensure compatibility with old OPA versions (e.g., v0.70.0 from before)
CMD ["run", "--server", "--v0-compatible", "-c", "config.yaml"]
