FROM local-only/base-python-cpu:latest

LABEL REGISTRY="local-only"
LABEL IMAGE="dag-installer"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

WORKDIR /app

COPY files/requirements.txt /app/
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

COPY files/run.py /app/run.py

CMD ["python3","-u","/app/run.py"]
