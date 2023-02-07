FROM local-only/base-python-cpu:latest

LABEL IMAGE="bin2dcm"
LABEL VERSION="3.6.4"
LABEL CI_IGNORE="False"

COPY files/template.xml /app/
COPY files/start.py /app/

CMD ["python3","-u","/app/start.py"]
