FROM python:3.9-alpine3.12

LABEL IMAGE="auth-check"
LABEL VERSION=""
LABEL CI_IGNORE="False"


WORKDIR /app
COPY files/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

ADD files/start.py /app/

CMD ["uvicorn", "start:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "8000"]
