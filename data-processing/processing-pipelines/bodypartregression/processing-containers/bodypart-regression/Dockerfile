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

# RUN apt-get purge -y libhwloc-dev libhwloc-plugins
# Clone directory from git
RUN git clone  --single-branch --branch master https://github.com/MIC-DKFZ/BodyPartRegression.git && cd BodyPartRegression && git checkout v1.1 

# Download public model from zenodo 
RUN touch BodyPartRegression/src/models/public_bpr_model.zip
RUN curl --location --header "Connection: Keep-Alive" --header "Keep-Alive: 300" https://zenodo.org/record/5113483/files/public_bpr_model.zip?download=1 -o /kaapana/app/BodyPartRegression/src/models/public_bpr_model.zip 
RUN echo "cc0ba26374932f0ca27452f4ad9bf9db /kaapana/app/BodyPartRegression/src/models/public_bpr_model.zip" | md5sum -c


RUN unzip BodyPartRegression/src/models/public_bpr_model.zip -d /kaapana/app/BodyPartRegression/src/models/

COPY files/requirements.txt /kaapana/app/
RUN pip3 uninstall -y torch torchtext torchaudio && pip3 install -c https://codebase.helmholtz.cloud/kaapana/constraints/-/raw/0.3.0/constraints.txt -r /kaapana/app/requirements.txt

WORKDIR /kaapana/app/BodyPartRegression

CMD ["python3", "-u", "starter.py"]
