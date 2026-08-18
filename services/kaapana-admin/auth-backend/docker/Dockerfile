FROM local-only/base-python-cpu:latest

LABEL IMAGE="auth-backend"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app

COPY ./files/requirements.txt /kaapana/app/requirements.txt
COPY --from=constraints 0.7.0.txt /constraints.txt
RUN pip install -c /constraints.txt --no-cache-dir --upgrade -r /kaapana/app/requirements.txt

COPY ./files/*.py /kaapana/app/
COPY ./files/*.html /kaapana/app/

# Version bump v0.70.0 -> v1.18.2 — fixes critical CVEs in the Go:
#   - Go stdlib:               CVE-2025-68121
#   - google.golang.org/grpc:  CVE-2026-33186
# Extra Infos:
#   - Required by the opa-build initContainer (auth-backend-chart/templates/deployment.yaml) 
#   - Compatibility is ensured with flag --v0-compatible there.
#   - Version should match with open-policy-agent service image (1.18.2)
RUN curl -L -o opa https://openpolicyagent.org/downloads/v1.18.2/opa_linux_amd64_static
RUN chmod 755 ./opa

COPY files/bundle/ bundle/
RUN mkdir -p /kaapana/app/authz
# RUN ./opa build -b bundle/ -o authz/endpoints.tar.gz

COPY files/boot.sh /kaapana/app
RUN chmod +x /kaapana/app/boot.sh

CMD ["/bin/sh", "/kaapana/app/boot.sh"]