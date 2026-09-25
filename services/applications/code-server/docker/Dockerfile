# code-server comes from the shared install image (base-images/base-code-server): the
# Python base images no longer carry it.
FROM local-only/base-code-server:latest AS code_server
FROM local-only/base-python-gpu:latest

LABEL IMAGE="code-server"
LABEL VERSION="4.10.1"
LABEL BUILD_IGNORE="False"

COPY --from=code_server /usr/lib/code-server /usr/lib/code-server
COPY --from=code_server /usr/bin/code-server /usr/bin/code-server
COPY --from=code_server /root/.local/share/code-server /root/.local/share/code-server
