FROM local-only/base-python-gpu:latest

LABEL IMAGE="total-segmentator"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

ENV SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True

WORKDIR /app

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    xvfb \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*


COPY files/requirements.txt /app/
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

COPY files/* /app/

CMD ["python3","-u","/app/total-segmentator.py"]
