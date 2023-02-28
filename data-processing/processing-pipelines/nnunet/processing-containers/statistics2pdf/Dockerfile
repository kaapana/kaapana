FROM local-only/base-python-cpu:latest

LABEL IMAGE="statistics2pdf"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="False"

WORKDIR /

# ToDo check if needed 
# RUN apk update && apk add --no-cache python3-dev gcc libc-dev  jpeg-dev zlib-dev && pip3 install --upgrade pip

COPY files/requirements.txt /
RUN pip3 install --no-cache-dir -r requirements.txt

COPY files/start.py /kaapana/app/
CMD ["python3","-u","/kaapana/app/start.py"]
