FROM local-only/base-python-cpu:latest

LABEL IMAGE="itk2dcm"
LABEL VERSION="v1.2.4"
LABEL CI_IGNORE="False"

COPY files/convert-itk2dcm.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/convert-itk2dcm.py"]