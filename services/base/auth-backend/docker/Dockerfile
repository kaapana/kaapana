FROM local-only/base-python-cpu:latest

LABEL IMAGE="auth-backend"
LABEL VERSION="0.0.0"
LABEL CI_IGNORE="False"

WORKDIR /app

COPY ./files/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./files/*.py /app/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
