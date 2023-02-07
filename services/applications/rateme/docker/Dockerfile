FROM local-only/base-python-cpu:latest

LABEL IMAGE="rateme"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /app

ENV SWIPE_APP=0d79877d422d888cd0dbb33ea1ec72fc18ceb7b0
ENV BRANCH=develop

# RUN git clone --single-branch --branch ${BRANCH} https://phabricator.mitk.org/source/swipe-app.git && cd swipe-app && git checkout ${SWIPE_APP_VERSION}
COPY files/rateme/requirements.txt /app/

RUN pip3 install --upgrade pip && pip3 install -r /app/requirements.txt

COPY files/rateme /app/rateme 


CMD ["python3","-u","/app/rateme/rateme.py"]    



