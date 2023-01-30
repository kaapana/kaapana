FROM local-only/base-python-cpu:latest

LABEL IMAGE="pyradiomics"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /app

COPY files/requirements.txt /app/
RUN python3 -m pip install --no-cache-dir -r /app/requirements.txt && rm /app/requirements.txt 

COPY files/pyradiomics.py /app/

CMD ["python3","-u","/app/pyradiomics.py"]
