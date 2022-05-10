FROM pytorchlightning/pytorch_lightning:base-cuda-py3.9-torch1.11

LABEL IMAGE="bodypartregression"
LABEL VERSION="v1.3"
LABEL CI_IGNORE="False"

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    git \
    htop \
    zip \
    unzip \
    curl \
    python3-opencv \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip3 install --upgrade pip

# Clone directory from git
RUN git clone  --single-branch --branch master https://github.com/MIC-DKFZ/BodyPartRegression.git && cd BodyPartRegression && git checkout v1.1 

# Download public model from zenodo 
RUN touch BodyPartRegression/src/models/public_bpr_model.zip
RUN curl https://zenodo.org/record/5113483/files/public_bpr_model.zip?download=1 -o BodyPartRegression/src/models/public_bpr_model.zip 

RUN unzip BodyPartRegression/src/models/public_bpr_model.zip -d BodyPartRegression/src/models/

WORKDIR /app/BodyPartRegression
COPY requirements.txt /files/requirements.txt
RUN pip3 install -r /files/requirements.txt

CMD ["python3", "-u", "starter.py"]
