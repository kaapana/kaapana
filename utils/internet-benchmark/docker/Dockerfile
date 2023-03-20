FROM python:3.8

LABEL IMAGE="speedtest"
LABEL VERSION="0.0.0"
LABEL CI_IGNORE="True"

COPY files/speedtest.py .

RUN apt update
RUN apt install -y vim
CMD ["python3", "-u", "speedtest.py"]