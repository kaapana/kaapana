FROM local-only/base-python-gpu:latest
# FROM nvcr.io/nvidia/pytorch:22.04-py3

LABEL IMAGE="total-segmentator"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app
ENV SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    xvfb \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*


COPY files/requirements.txt /kaapana/app/
RUN python -m pip install -c https://raw.githubusercontent.com/kaapana/kaapana/develop/build-scripts/constraints-0.1.3.txt --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/total-segmentator.py"]
