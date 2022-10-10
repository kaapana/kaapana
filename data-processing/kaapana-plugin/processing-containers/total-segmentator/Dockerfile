FROM local-only/base-python-cpu:0.1.0

LABEL IMAGE="total-segmentator"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="True"

COPY files/mint-input-validator.py /kaapanasrc/
COPY files/requirements.txt /root/
RUN pip3 install -r /root/requirements.txt

CMD ["python3","-u","/kaapanasrc/total-segmentator.py"]