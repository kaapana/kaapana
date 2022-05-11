FROM local-only/base-python-alpine:0.1.0

LABEL IMAGE="statistics2pdf"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r requirements.txt

COPY files/start.py /
CMD ["python3","-u","/start.py"]
