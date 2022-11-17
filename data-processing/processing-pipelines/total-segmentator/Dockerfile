FROM local-only/base-python-gpu:0.1.0

LABEL IMAGE="total-segmentator"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="True"

RUN apt-get update && apt-get install -y xvfb

COPY files/total-segmentator.py /kaapanasrc/
COPY files/seg_info.json /kaapanasrc/
COPY files/requirements.txt /root/
RUN pip3 install -r /root/requirements.txt

WORKDIR /kaapanasrc/
CMD ["python3","-u","/kaapanasrc/total-segmentator.py"]
