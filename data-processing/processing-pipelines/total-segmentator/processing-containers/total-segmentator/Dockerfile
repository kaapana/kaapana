FROM local-only/base-python-gpu:latest

LABEL IMAGE="total-segmentator"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="False"

WORKDIR /kaapana/app
ENV SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    xvfb \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY files/requirements.txt /kaapana/app/
# manually install torch 2.5.1
RUN python3 -m pip install torch torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118
RUN python -m pip install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.4.0/constraints.txt --no-cache-dir -r /kaapana/app/requirements.txt

COPY files/* /kaapana/app/

CMD ["python3","-u","/kaapana/app/start-total-segmentator.py"]
