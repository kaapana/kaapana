
FROM python:3.8-slim-buster
# FROM nvcr.io/nvidia/pytorch:20.09-py3 
# FROM nvcr.io/nvidia/pytorch:21.01-py3
# This image makes trubles - pandas and skipy cant be found
# FROM python:3.8-slim-buster

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
RUN pip3 install -e .

CMD ["python3", "-u", "starter.py"]
