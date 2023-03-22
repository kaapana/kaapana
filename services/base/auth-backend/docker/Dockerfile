FROM local-only/base-python-cpu:latest

LABEL IMAGE="auth-backend"
LABEL VERSION="0.0.0"
LABEL CI_IGNORE="False"

WORKDIR /kaapana/app

COPY ./files/requirements.txt /kaapana/app/requirements.txt
RUN pip install -c https://raw.githubusercontent.com/kaapana/kaapana/develop/build-scripts/constraints-0.1.3.txt --no-cache-dir --upgrade -r /kaapana/app/requirements.txt

COPY ./files/*.py /kaapana/app/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
