FROM local-only/base-python-gpu:latest

LABEL IMAGE="bodypartregression"
LABEL VERSION="v1.3"
LABEL BUILD_IGNORE="False"

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /kaapana/app

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

# Clone directory from git
RUN git clone https://github.com/MIC-DKFZ/BodyPartRegression.git && cd BodyPartRegression && git checkout 7f66baa

# Download public model from zenodo with retries/resume (Zenodo supports range
# requests); truncated transfers have failed release builds here. The md5sum
# check below stays as the integrity gate.
RUN curl -sS -L -f -C - --retry 20 --retry-all-errors --retry-delay 10 \
        -o /kaapana/app/BodyPartRegression/src/models/public_bpr_model.zip \
        "https://zenodo.org/record/5113483/files/public_bpr_model.zip?download=1"
RUN echo "cc0ba26374932f0ca27452f4ad9bf9db /kaapana/app/BodyPartRegression/src/models/public_bpr_model.zip" | md5sum -c
RUN unzip BodyPartRegression/src/models/public_bpr_model.zip -d /kaapana/app/BodyPartRegression/src/models/

RUN pip3 uninstall -y torch torchtext torchaudio &&  \
    pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.7.0/constraints.txt /kaapana/app/BodyPartRegression/ && \
    pip3 install pytorch-lightning==2.6.5

# Fix CVE-2024-8019/CVE-2024-8020 (critical): force patched pytorch-lightning.
RUN pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.7.0/constraints.txt "pytorch-lightning==2.4.0"


WORKDIR /kaapana/app/BodyPartRegression

CMD ["python3", "-u", "starter.py"]
