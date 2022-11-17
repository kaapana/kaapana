FROM local-only/base-python-gpu:latest

LABEL IMAGE="total-segmentator"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="True"

RUN apt-get update && apt-get install -y xvfb

COPY processing-containers/total-segmentator/files/total-segmentator.py /kaapanasrc/
COPY processing-containers/total-segmentator/files/seg_info.json /kaapanasrc/
COPY processing-containers/total-segmentator/files/requirements.txt /root/
RUN pip3 install -r /root/requirements.txt

WORKDIR /kaapanasrc/
CMD ["python3","-u","/kaapanasrc/total-segmentator.py"]
