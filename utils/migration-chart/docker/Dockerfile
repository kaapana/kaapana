FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Remove default non-root user 1000
RUN userdel -r ubuntu || true

LABEL IMAGE="migration"
LABEL BUILD_IGNORE="False"

# Install required packages: python3, pip, curl, bash, docker CLI
RUN apt-get update && \
    apt-get install -y python3 python3-pip curl bash docker.io && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /kaapana/app

COPY files/* /kaapana/app/

# Make bash scripts executable
RUN chmod +x /kaapana/app/*.sh

# Default command to run migration script
CMD ["python3","-u","/kaapana/app/migration.py"]
