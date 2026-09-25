FROM local-only/base-code-server:latest

LABEL IMAGE="code-server-init"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

# Init container of dev-server-chart: hands code-server and its Python extension to the
# task container through two shared volumes, so the task image needs no code-server of
# its own (any glibc-based image with python will do). The chart mounts the same volumes
# in the main container at /usr/lib/code-server and
# /root/.local/share/code-server/extensions, where code-server expects them.
CMD ["sh", "-c", "cp -a /usr/lib/code-server/. /mnt/code-server/ && cp -a /root/.local/share/code-server/extensions/. /mnt/code-server-extensions/"]
