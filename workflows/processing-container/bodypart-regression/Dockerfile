FROM local-only/base-pytorch-gpu:0.1.0

LABEL IMAGE="bodypartregression"
LABEL VERSION="v1.3"
LABEL CI_IGNORE="False"

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends python3-opencv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /kaapanasrc

# Clone directory from git
RUN git clone  --single-branch --branch master https://github.com/MIC-DKFZ/BodyPartRegression.git && cd BodyPartRegression && git checkout v1.1 

# Download public model from zenodo 
RUN touch BodyPartRegression/src/models/public_bpr_model.zip
RUN curl https://zenodo.org/record/5113483/files/public_bpr_model.zip?download=1 -o BodyPartRegression/src/models/public_bpr_model.zip 

RUN unzip BodyPartRegression/src/models/public_bpr_model.zip -d BodyPartRegression/src/models/

WORKDIR /kaapanasrc/BodyPartRegression
COPY files/requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt

CMD ["python3", "-u", "starter.py"]
