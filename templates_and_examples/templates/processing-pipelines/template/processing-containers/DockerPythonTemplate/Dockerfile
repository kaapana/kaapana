# # With cuda
FROM local-only/base-python-gpu:latest

# Without cuda
FROM local-only/base-python-cpu:latest

LABEL IMAGE="python-template"
LABEL VERSION="0.1.0"
LABEL CI_IGNORE="True"

COPY files/requirements.txt /src
RUN pip3 install -r /src/requirements.txt

COPY files/start.py /

CMD ["python3","-u","/start.py"]