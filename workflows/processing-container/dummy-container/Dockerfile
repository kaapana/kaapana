FROM python:3.9-alpine3.12

LABEL IMAGE="dummy_container"
LABEL VERSION="0.1.1"
LABEL CI_IGNORE="False"

WORKDIR /
RUN pip3 install --upgrade pip

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r requirements.txt

COPY files/dummy.py /

CMD ["python","-u","/dummy.py"]
