FROM local-only/base-python-cpu:latest

LABEL IMAGE="itk2dcm"
LABEL VERSION="v1.2.4"
LABEL CI_IGNORE="False"

COPY files/requirements.txt /kaapanasrc/
RUN pip3 install -r /kaapanasrc/requirements.txt

COPY files/convert-itk2dcm.py /kaapanasrc/
COPY files/dicom_tags_current.csv /kaapanasrc/

CMD ["python3","-u","/kaapanasrc/convert-itk2dcm.py"]