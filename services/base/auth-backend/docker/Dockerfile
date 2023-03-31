FROM local-only/base-python-cpu:latest

LABEL IMAGE="auth-backend"
LABEL VERSION="0.0.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

# Create a group "kaapana" and user "kaapana" with minimal rights
RUN addgroup -gid 1000 kaapana && \
    adduser -D -H -u 1000 -s /bin/sh -G kaapana kaapana

COPY ./files/*.py /kaapana/app/
COPY ./files/*.html /kaapana/app/

# Set "kaapana" as the owner of the /kaapana/app directory
RUN chown -R 1000:1000 /kaapana/app

# Switch to the "kaapana" user for security reasons
USER kaapana

COPY ./files/requirements.txt /kaapana/app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /kaapana/app/requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
