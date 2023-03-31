FROM local-only/base-python-cpu:latest

LABEL IMAGE="service-checker"
LABEL VERSION="1.1"
LABEL CI_IGNORE="False"

# Create a group "kaapana" and user "kaapana" with minimal rights
RUN addgroup -gid 1000 kaapana && \
    adduser -D -H -u 1000 -s /bin/sh -G kaapana kaapana

COPY files/service_checker.py /service_checker.py

# Set "kaapana" as the owner of the /service_checker.py file
RUN chown 1000:1000 /service_checker.py

# Switch to the "kaapana" user for security reasons
USER kaapana

RUN pip install --no-cache-dir requests==2.27.1

CMD [ "python3", "-u","/service_checker.py" ]
