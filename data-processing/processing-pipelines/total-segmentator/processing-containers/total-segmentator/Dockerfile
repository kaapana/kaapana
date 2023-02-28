FROM local-only/base-python-gpu:latest

LABEL IMAGE="total-segmentator"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

<<<<<<< HEAD
ENV SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True

WORKDIR /app

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    xvfb \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*
=======
WORKDIR /kaapana/app

COPY files/requirements.system /kaapana/app/
RUN apt-get update -y && cat /kaapana/app/requirements.system | xargs apt-get install -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*
>>>>>>> b0d47d1c823a51dd3af874a59ed61ecd4d468b94


COPY files/requirements.txt /kaapana/app/
RUN python -m pip install --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/total-segmentator.py"]
