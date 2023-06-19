FROM local-only/base-python-cpu:latest
LABEL IMAGE="example_nifti_conv"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"
#WORKDIR /tmp

RUN pip install pynrrd
RUN pip install nilearn
RUN pip install pyyaml


COPY files/main.py /kaapana/app/

CMD ["python3","-u","/kaapana/app/main.py"]
