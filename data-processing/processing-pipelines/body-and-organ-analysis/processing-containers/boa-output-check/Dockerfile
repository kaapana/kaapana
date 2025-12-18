FROM local-only/base-python-cpu:latest

LABEL IMAGE="boa-output-check"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"
    
COPY files/requirements.txt /kaapana/app/requirements.txt
RUN pip install --upgrade pip && pip install -r /kaapana/app/requirements.txt

COPY files/ /kaapana/app/

CMD ["python3","-u","/kaapana/app/boa_output_check.py"]