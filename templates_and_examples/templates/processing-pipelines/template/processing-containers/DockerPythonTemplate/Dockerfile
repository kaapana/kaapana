# # With cuda
FROM local-only/base-python-gpu:latest

# Without cuda
FROM local-only/base-python-cpu:latest

LABEL IMAGE="python-template"
LABEL VERSION="0.1.0"
LABEL BUILD_IGNORE="True"

COPY files/start.py /

CMD ["python3","-u","/start.py"]