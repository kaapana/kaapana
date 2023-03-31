FROM local-only/base-python-cpu:latest

LABEL IMAGE="kaapana-backend"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

# Create a group "kaapana" and user "kaapana" with minimal rights
RUN addgroup -gid 1000 kaapana && \
    adduser -D -H -u 1000 -s /bin/sh -G kaapana kaapana

COPY files/ /kaapana/app
RUN chmod +x /kaapana/app/boot.sh

# Set "kaapana" as the owner of the /kaapana/app directory
RUN chown -R 1000:1000 /kaapana/app

# Switch to the "kaapana" user for security reasons
USER kaapana

# pip install after user switch to avoid permission issues
COPY files/requirements.txt /kaapana/app/
RUN python -m pip install --no-cache-dir -r /kaapana/app/requirements.txt

ENTRYPOINT ["/kaapana/app/boot.sh"]
