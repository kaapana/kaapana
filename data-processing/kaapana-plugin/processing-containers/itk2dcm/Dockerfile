FROM local-only/base-python-cpu:latest

LABEL IMAGE="itk2dcm"
LABEL VERSION="v1.2.4"
LABEL CI_IGNORE="True"

COPY files/requirements.txt /src/
RUN pip3 install -r /src/requirements.txt

COPY files/convert-itk2dcm.py /src/
COPY files/dicom_tags_current.csv /src/

CMD ["python3","-u","/src/convert-itk2dcm.py"]