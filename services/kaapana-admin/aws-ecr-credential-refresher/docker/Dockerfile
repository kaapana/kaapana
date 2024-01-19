FROM local-only/base-python-cpu:latest

LABEL IMAGE="update-k8s-secret"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="False"

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY update_k8s_secret.py .

CMD ./update_k8s_secret.py
